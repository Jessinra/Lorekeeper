---
name: lorekeeper-code-reviewer
description: "Lorekeeper-specific BLOCKER patterns, severity tiers, and review checklist — used when reviewing any PR touching src/lorekeeper/"
version: 1.1.0
author: Diana
---

# Lorekeeper Code Review Patterns

Use this skill when reviewing any PR that changes `src/lorekeeper/` runtime code, services, handlers, or MCP server. These are project-specific patterns that general-purpose review prompts miss.

Load alongside `github-code-review` for a complete review session.

## Severity Tiers

Every review comment **must** carry a severity label.

| Label         | Tier       | Merge impact                      |
| ------------- | ---------- | --------------------------------- |
| `blocker:`    | 🔴 BLOCKER | **Must fix before merge**         |
| `issue:`      | 🟠 MAJOR   | Fix before merge or create ticket |
| `suggestion:` | 🟡 MINOR   | Fix encouraged, deferrable        |
| `nit:`        | 🔵 NIT     | Optional, never blocks            |
| `praise:`     | ✅         | Acknowledge good work             |

**Merge contract:** PR is mergeable when all BLOCKERs resolved, all MAJORs resolved OR tracked, CI green, ≥1 human approval.

## 🔴 BLOCKER Patterns — Lorekeeper-Specific

These are always BLOCKER. They are the patterns most commonly missed by general review.

### 1. print() in runtime code → MCP protocol corruption

```python
# BLOCKER — stdout is reserved for MCP JSON-RPC
print(f"Added memory: {lore_id}")

# CORRECT
logger = structlog.get_logger()
logger.info("Memory added", lore_id=lore_id)
```

**Check:** every `print(` in `src/lorekeeper/`. CLI tools (scripts/, **main**.py) are exempt. `log.exception()` goes to stderr — fine.

### 2. mem0.add() without infer=False → silent LLM call

```python
# BLOCKER — infer=True is default, silently invokes LLM
await self.mem0.add(messages=[{"role": "user", "content": text}], user_id=user_id)

# CORRECT
await self.mem0.add(messages=[{"role": "user", "content": text}], user_id=user_id, infer=False)
```

### 3. Exposing Mem0 internal id instead of lore_id

```python
# BLOCKER — mem0 internal id is meaningless outside the store
return {"id": result["id"], "content": result["memory"]}

# CORRECT
return {"lore_id": result["metadata"]["lore_id"], "content": result["memory"]}
```

### 4. SQL injection — f-string in execute()

```python
# BLOCKER
conn.execute(f"SELECT * FROM memories WHERE title LIKE '%{query}%'")

# CORRECT
conn.execute("SELECT * FROM memories WHERE title LIKE ?", (f"%{query}%",))
```

### 5. Bare except swallowing failures

```python
# BLOCKER — swallows KeyboardInterrupt, SystemExit
try:
    result = await service.search(query)
except:
    pass

# CORRECT
try:
    result = await service.search(query)
except LorekeeperError as e:
    logger.exception("Search failed", query=query)
    raise
```

### 6. Blocking I/O in async context

```python
# BLOCKER — blocks the event loop
async def fetch_related(url: str) -> dict:
    response = requests.get(url, timeout=10)

# CORRECT — use httpx async
async def fetch_related(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
    return response.json()
```

### 7. MCP contract violations

- Rename, removal, or schema change to existing MCP tools without explicit versioning
- New `@mcp.tool` added without README docs and `check_mcp_docs.py` update
- Response fields dropped or renamed
- Tool added but not listed in `assets/prompts/lorekeeper-agent-prompt.md`

### 8. Migration violations

- Modifying existing `MIGRATIONS[0]` entry (the bootstrap migration) — must never be changed
- New schema changes not added via `MIGRATIONS.append((N, name, fn))` with strictly-increasing version numbers

### 9. Handler returns error dict instead of raising

```python
# BLOCKER — makes failures invisible to MCP client
except Exception:
    return {"error": "search failed", "candidates": []}

# CORRECT — let MCP propagate the error
except Exception:
    log.exception("search_failed")
    raise
```

### 10. Missing commit() after SQLite DML (IR-002)

```python
# BLOCKER — DML without commit loses data on process crash
conn.execute("UPDATE config SET value = ? WHERE key = ?", (val, key))

# CORRECT
conn.execute("UPDATE config SET value = ? WHERE key = ?", (val, key))
conn.commit()
```

**Check:** Every `conn.execute()` that does INSERT, UPDATE, DELETE, or REPLACE must have a
corresponding `conn.commit()`. The same connection reads its own transaction buffer, so
missing commits pass tests but lose data on restart.

### 11. Shared sqlite3.Connection across threads (IR-002)

```python
# BLOCKER — check_same_thread=False removes the guard but not the race
conn = sqlite3.connect(str(path), check_same_thread=False)
self.mcp_store = MemoryStore(conn)
self.sweep_store = MemoryStore(conn)  # different thread!

# CORRECT — each thread gets its own connection
mcp_conn = sqlite3.connect(str(path))
sweep_conn = sqlite3.connect(str(path), check_same_thread=False)
self.mcp_store = MemoryStore(mcp_conn)
self.sweep_store = MemoryStore(sweep_conn)
```

**Check:** Background threads (sweep, scheduler, periodic jobs) must always receive their
own Database instance. Never pass a single connection to ≥2 threads, even with
`check_same_thread=False`.

### 12. Timer set after job instead of before (IR-002 — infinite retry storm)

```python
# BLOCKER — if job crashes, timer is never updated → infinite restarts
result = await self._run_job()
await self._save_timer(next_run)  # never reached on crash

# CORRECT — set timer before running job
await self._save_timer(next_run)
try:
    result = await self._run_job()
except Exception:
    await self._save_timer(next_run + fallback_interval)
    raise
```

**Check:** Any periodic job must write its next-run timestamp _before_ executing the
work, not after. A post-crash fallback (retry in N minutes, not instant) is mandatory.

### 13. Concurrent processes writing to the same SQLite DB (IR-002)

```python
# BLOCKER — two separate processes both write to lorekeeper.db → contention
# Server process: writes memories, config to lorekeeper.db
# Sweep process: writes link_suggestions, metrics to lorekeeper.db ← CONTENTION

# CORRECT — separate DB files for separate workloads
# Server writes to: lorekeeper.db
# Sweep writes to: sweep.db (dedicated file, server never touches it)
```

**Check:** If two independent subsystems both write to SQLite, they must use different
`.db` files. `busy_timeout` is a band-aid; structural separation eliminates contention.

## 🟠 MAJOR Review Priorities

Check in this order:

### Correctness

- Missing `None` checks before attribute access on Optional values
- Multi-step DB writes not wrapped in a transaction boundary
- Off-by-one in pagination, window sizes, score calculations
- Race conditions in concurrent memory access

### Service layer discipline

- Direct `conn.execute()` in handler or server code — must go through store classes
- Test that calls `asyncio.run()` directly instead of using `pytest-asyncio` fixtures

### Performance

- **N+1 queries** — DB calls inside a loop
- Unbounded `.all()` or `.fetchall()` without pagination

### Testing

- New business logic without tests (happy path + ≥1 error case)
- Changes to scoring, dedup, or soft-delete without regression tests
- Test assertions that only check "didn't raise" instead of actual output
- E2E tests added/changed but not run locally before PR

### Dead instance attributes

Cross-reference `self.X =` assignments in `__init__` against all method bodies. ruff does NOT flag unused instance attributes. Common: `self._tau = tau_days` computed alongside a validated `self._td = ...`; original never read.

### Alternative paths missing side effects

When a PR adds a fast path / bypass (e.g. `ids` bulk-lookup that skips search pipeline), verify it still fires every side effect the main path does: metrics, usage_count bump, cache invalidation, audit log.

## 🟡 MINOR Items

- Type annotations missing on public function signatures
- Functions >50 lines — flag for potential extraction
- Magic numbers not in named constants or `Settings`
- Dead code, commented-out blocks, unused imports
- `logging.error()` in except blocks — should be `logging.exception()`

## 🔵 NIT — Never Block

- Import order (handled by ruff — do not comment)
- Line length (handled by ruff — do not comment)
- Minor naming preferences when current name is already clear
- Test coverage numbers (pytest-cov enforces)

## Repo-Specific Red Flags

These indicate misunderstanding of the architecture — flag immediately:

- Any `print(` in `src/lorekeeper/` not inside a CLI tool
- `mem0.add(...)` without `infer=False`
- Direct `conn.execute()` in handler or server code
- Changes to `MIGRATIONS[0]`
- Importing from `dashboard/` in server code (wrong dep direction)
- Adding `import requests` to `server.py` — use `httpx` async
- DML without `commit()` in config_store, memory_store, or any service
- Shared `sqlite3.Connection` across threads (sweep + MCP)
- Timer-after-job pattern in scheduler — must be timer-before-job
- Two subsystems (sweep + server) writing to same `.db` file

## Review Style Rules

- Reference exact file:line (`server.py:112`)
- Show the fix, not just the problem
- Bullet points, not paragraphs
- **Comment only on the diff** — don't flag pre-existing issues
- Use `praise:` when something is done well
- Always explain rationale for BLOCKER/MAJOR items

## What NOT to Comment On (automation handles)

- Import order → ruff
- Line length, whitespace → ruff
- Type errors → mypy (CI)
- Coverage → pytest-cov (CI)
- Markdown formatting → prettier (CI)
- Skill format → check_skills.py (CI)
