# BLOCKER Patterns — Lorekeeper-Specific

These are always BLOCKER. They are the patterns most commonly missed by general review.

## Pre-check: Does this PR touch src/lorekeeper/?

**Before diving into any BLOCKER pattern, run this check first:**

```bash
git diff main...HEAD --name-only | grep -q "^src/lorekeeper/" && echo "RUNTIME PR" || echo "NON-CODE PR"
```

- **RUNTIME PR** → apply all BLOCKER patterns below.
- **NON-CODE PR** (docs, landing, CI, configs, tests) → all 12 patterns are N/A.

## 1. print() in runtime code → MCP protocol corruption

```python
# BLOCKER — stdout is reserved for MCP JSON-RPC
print(f"Added memory: {lore_id}")

# CORRECT
logger = structlog.get_logger()
logger.info("Memory added", lore_id=lore_id)
```

**Check:** every `print(` in `src/lorekeeper/`. CLI tools (scripts/, `__main__.py`) exempt.

## 2. mem0.add() without infer=False → silent LLM call

```python
# BLOCKER
await self.mem0.add(messages=[...], user_id=user_id)

# CORRECT
await self.mem0.add(messages=[...], user_id=user_id, infer=False)
```

## 3. Exposing Mem0 internal id instead of lore_id

```python
# BLOCKER — mem0 internal id is meaningless outside the store
return {"id": result["id"], "content": result["memory"]}

# CORRECT
return {"lore_id": result["metadata"]["lore_id"], "content": result["memory"]}
```

## 4. SQL injection — f-string in execute()

```python
# BLOCKER
conn.execute(f"SELECT * FROM memories WHERE title LIKE '%{query}%'")

# CORRECT
conn.execute("SELECT * FROM memories WHERE title LIKE ?", (f"%{query}%",))
```

## 5. Bare except swallowing failures

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

## 6. Blocking I/O in async context

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

## 7. MCP contract violations

- Rename, removal, or schema change to existing MCP tools without explicit versioning
- New `@mcp.tool` added without README docs and `check_mcp_docs.py` update
- Response fields dropped or renamed
- Tool added but not listed in `assets/prompts/lorekeeper-agent-prompt.md`

## 8. Migration violations

- Modifying existing `MIGRATIONS[0]` entry (bootstrap migration) — must never be changed
- New schema changes not added via `MIGRATIONS.append((N, name, fn))` with strictly-increasing version numbers
- **Enum migration map semantic direction inversions** — e.g. `"used_by" → "depends_on"` inverts the subject/object role. Old `(A, used_by, B)` meant "B uses A", but `(A, depends_on, B)` reads "A depends on B". Any mapping that reverses direction is a BLOCKER if undocumented:
  - Comment on the mapping must spell out the inversion
  - PR description must flag it as intentional with rationale
  - Migration test must verify the stored value reads back as the new type

Detection: for each entry in the map, check whether the new type name implies the SAME direction as the old name from the perspective of the source node. Most `"used_*"` → semantic-type mappings invert.

## 9. Datetime sort on raw strings — silently wrong ordering

```python
# BLOCKER — lexicographic, not chronological
results.sort(key=lambda r: r.memory.updated_at, reverse=True)

# CORRECT — parse to UTC datetime first
results.sort(key=lambda r: parse_iso_utc(r.memory.updated_at), reverse=True)
```

Lorekeeper stores timestamps as ISO 8601 strings. Two formats coexist:

- Naive: `'2026-06-01T00:00:00'` (pre-migration rows)
- Offset-aware: `'2026-06-01T00:00:00+00:00'` (new rows)

String comparison of mixed formats is chronologically wrong. Always use `parse_iso_utc()` (public, in `services/search.py`). Do NOT use the `_parse_iso_utc` alias.

## 10. Dict-key validation gap in `_handle_insert`

Lorekeeper has two structural surfaces for validated params:

- **Surface A** — typed function signatures (`lore_search`, `lore_remember`): validation is explicit
- **Surface B** — per-memory dict loop in `_handle_insert`: same param arrives as untyped string key, validation is easily forgotten

When a new validated enum is added to surface A, it MUST also be validated in `_handle_insert`'s `for i, m in enumerate(memories):` loop. Omission means `lore_insert` silently accepts arbitrary values while `lore_search` and `lore_remember` reject them.

**Check:** any new validated enum in `lore_search`/`lore_remember` — verify the same value is checked in `_handle_insert`. Always use the **write-safe** constant (e.g. `WRITE_SOURCE_TYPES`), not the full set. Reserved values like `'unknown'` for migration backfill must NOT be writable by callers.

## 11. Reserved enum values reachable on write paths

For enum fields with internal-only values, define two constants:

```python
SOURCE_TYPES: frozenset[str] = frozenset(get_args(SourceType))     # all values — reads
WRITE_SOURCE_TYPES: frozenset[str] = SOURCE_TYPES - {"unknown"}    # caller-writable — writes
```

- Read paths → `SOURCE_TYPES`
- Write paths → `WRITE_SOURCE_TYPES`
- Model field → use the Literal type alias, not `str`

## 12. Handler returns error dict instead of raising

```python
# CORRECT — let MCP propagate the error
except Exception:
    log.exception("search_failed")
    raise
```

## 13. Server wiring type mismatch — wrong object passed where a specific dependency is expected

```python
# BLOCKER — MemoryService passed where ConfigStore expected
PeriodicJob(
    svc, svc.sweep_links, "sweep",  # ← svc is MemoryService, has self.config but is not a ConfigStore
    ...
).start()
# Runtime crash on server start: AttributeError: 'MemoryService' object has no attribute 'get_overrides'

# CORRECT — pass the actual ConfigStore
PeriodicJob(
    svc.config, svc.sweep_links, "sweep",
    ...
).start()
```

**Check:** For every new subsystem wired in `server.py`, trace the constructor type annotations. If a param is typed as `ConfigStore`, `Database`, `LinkStore`, etc., verify the passed value is that exact type — not a larger object (like `MemoryService`) that happens to _contain_ it. The type checker (mypy) catches this if the annotations are correct; the risk is when the param is `Callable`-typed and the annotation doesn't constrain the first positional argument.

Common failure pattern: `PeriodicJob.__init__(self, config: ConfigStore, job_fn: Callable, ...)` — the `config` param is typed but `job_fn` is a generic callable, so passing `svc` (wrong first arg) doesn't trigger a type error if the positional order is confused. Always read the constructor signature, not just the call site.

## 14. Function defined but never called from any production path

When a PR adds a public method to `MemoryService` (or any orchestrator) that has identical or near-identical logic to a standalone service class, only one should be the production path:

```python
# BLOCKER — two copies of the same algorithm, only one reachable from server.py
class MemoryService:
    def sweep_links(self) -> dict[str, Any]:   # ← defined, tested, but NEVER called
        """..."""
        for mem_id in all_mems:
            ...  # identical logic to SweepService.run()

# server.py uses SweepService.run() instead:
sweep_svc = SweepService(...)
PeriodicJob(config, sweep_svc.run, "sweep", ...).start()
# → MemoryService.sweep_links() is dead code
```

**Check:** After reviewing any new method on MemoryService (or orchestrator), trace the call graph: find every call site in `server.py`, `scripts/`, and test files. If the only callers are tests and no production path reaches it, that method is dead code. The dead code itself is MAJOR (it will be found and removed), but the **duplication** (identical algorithm in two places) is BLOCKER because future fixes only land in one copy, leaving invalid behaviour in the other.

**Exception:** Methods intentionally exposed as test helpers / public API for programmatic callers should be annotated with a docstring noting the intended caller, e.g. `"""Public API — used by scripts/sweep-links.py."""`.

## 15. CLI script calls method that doesn't exist on the target

When a PR adds a new standalone service class (e.g. `SweepService`) and wires it in `server.py`, but also ships a CLI script (`scripts/sweep-*.py`) that references the same operation — verify the script calls methods that **actually exist**.

```python
# BLOCKER — runtime crash when run as non-dry-run
stats = svc.sweep_links()  # ← MemoryService has no sweep_links method!

# CORRECT — use the standalone SweepService
from lorekeeper.services.sweep_service import SweepService
sweeper = SweepService(memory_store, ..., conn=conn)
stats = sweeper.run()
```

**Check — for every new `scripts/*.py` in a PR:**

1. Read the script end-to-end, not just the diff
2. Trace every `svc.*()` / `stores.*()` call against the actual class it's called on — verify the method exists on that class
3. Examine ALL code paths, not just the first one (dry-run vs non-dry-run, `--help`, error cases)
4. Verify the server wiring path (e.g. `PeriodicJob → SweepService.run()`) uses the same call the script does — if they diverge, one path is broken
5. Run the script against a real (or temp) data directory to verify it doesn't crash on import

**Common failure pattern:** The server path uses `SweepService.run()` (correct standalone service), but the CLI script was written to the original plan which assumed `MemoryService.sweep_links()`. The plan was revised during implementation but the script wasn't updated. The dry-run sample path works (accesses `svc._link_candidate_generator.generate()` directly), so the broken non-dry-run path is invisible until someone actually runs the script for real.

## 15. CLI script calls method that doesn't exist on the target

When a PR adds a new standalone service class (e.g. `SweepService`) and wires it in `server.py`, but also ships a CLI script (`scripts/sweep-*.py`) that references the same operation — verify the script calls methods that **actually exist**.

```python
# BLOCKER — runtime crash when run as non-dry-run
stats = svc.sweep_links()  # ← MemoryService has no sweep_links method!

# CORRECT — use the standalone SweepService
from lorekeeper.services.sweep_service import SweepService
sweeper = SweepService(memory_store, ..., conn=conn)
stats = sweeper.run()
```

**Check — for every new `scripts/*.py` in a PR:**

1. Read the script end-to-end
2. Trace every `svc.*()` / `stores.*()` call against the actual class it's called on
3. Try all code paths, not just the first one (dry-run vs non-dry-run, `--help`, etc.)
4. Verify the server wiring path (PeriodicJob → SweepService.run()) gets the same call the script does — if they diverge, one path is broken

**Common failure pattern:** The server path uses `SweepService.run()` (a correct standalone service), but the CLI script was written to the original plan which assumed `MemoryService.sweep_links()`. The plan was revised during implementation but the script wasn't updated — the dry-run sample path works (uses `svc._link_candidate_generator.generate()` directly), but the real execution path crashes.

## 16. Missing commit() after SQLite DML → data loss on crash

Every `INSERT`, `UPDATE`, `DELETE`, or `executescript()` call on a `sqlite3.Connection` must be followed by `commit()`. Python's sqlite3 buffer starts an implicit `BEGIN` on the first DML statement; without an explicit `commit()` the change lives ONLY in the connection's in-memory buffer. The same connection reads it back (via subsequent SELECTs), so the writer can see its own change — but it was never written to the `.db` file. On crash or SIGKILL, the pending BEGIN rolls back and the change is lost forever.

```python
# BLOCKER — change lives in buffer, vanishes on crash
self._conn.execute("INSERT INTO config_overrides (key, value) VALUES (?, ?)", (key, val))
#        ↳ implicit BEGIN — never committed!

# CORRECT — always commit after DML
self._conn.execute("INSERT INTO config_overrides (key, value) VALUES (?, ?)", (key, val))
self._conn.commit()
```

**Exceptions:**

- DML inside an explicit `BEGIN` / `COMMIT` block managed by the caller
- Stores that are used exclusively by code paths that call `commit()` externally (e.g. dashboard routes that call `svc.commit()` after calling `set_override`) — but this is fragile; prefer self-contained commits

**Check:** For every new `conn.execute()` with INSERT/UPDATE/DELETE/DELETE FROM/executescript, verify a `commit()` follows within the same function (not deferred to a caller). Scan all existing stores for missing commits — this is a silent data-loss bug that passes all tests (tests connect, write, read back success, then close — the implicit transaction buffer makes it look persisted).

**Origin:** P0 Incident 2026-06-21 — `ConfigStore.set_override()` and `delete_override()` had missing `commit()` from introduction (PR #237/`ff3639c4`).

## 17. Background thread shares sqlite3.Connection with main thread → transaction corruption

When a daemon thread (e.g. `PeriodicJob` running `SweepService.run()`) shares the same `sqlite3.Connection` as the main MCP thread, concurrent writes corrupt transactions. Even with `check_same_thread=False` (which disables Python's safety check), Python's sqlite3 module provides **zero thread synchronisation** — two threads calling `execute()` simultaneously can interleave their statements inside the same BEGIN/COMMIT block.

```python
# BLOCKER — both threads use the same connection
db = Database(sqlite_path)
sweep_svc = SweepService(conn=db.conn, ...)   # ← same connection as main thread
PeriodicJob(config, sweep_svc.run, "sweep").start()

# CORRECT — sweep gets its OWN Database + store instances
sweep_db = Database(sqlite_path)
sweep_svc = SweepService(conn=sweep_db.conn, ...)
PeriodicJob(config, sweep_svc.run, "sweep").start()
```

**Check:** For every `PeriodicJob` (or any background daemon thread that performs writes), verify it has its own `Database` instance with a separate `sqlite3.Connection`. WAL mode handles concurrent access at the database-file level between the two connections — but only if they are genuinely separate objects.

**Origin:** P0 Incident 2026-06-21 — sweep thread shared `db.conn` with main thread (pre-PR #240), causing transaction corruption on every sweep run.

## 18. Scheduler sets next-run timer AFTER the job — infinite retry storm on crash

`PeriodicJob._loop` or any scheduler pattern that advances the next-run timestamp **after** the job callback executes will create an infinite retry loop if the job crashes: the timer is never written, the scheduler sees no next-run key, and fires the job again at the next poll cycle.

```python
# BLOCKER — timer never written if job crashes → infinite retry
next_time = datetime.now(UTC) + timedelta(hours=12)
self._config.set_override(self._timer_key, next_time.isoformat())
stats = self._job_fn()  # ← if this crashes, timer is already written — safe

# BETTER (hybrid) — short retry timer before, full interval on success
retry_time = datetime.now(UTC) + timedelta(minutes=11)
self._config.set_override(self._timer_key, retry_time.isoformat())
stats = self._job_fn()                                          # crash → 11 min retry
next_time = datetime.now(UTC) + timedelta(hours=12)             # success → 12h
self._config.set_override(self._timer_key, next_time.isoformat())
```

**Principle:** The retry/crash guard timer must be set BEFORE the job fires. On crash the timer is already advanced, preventing immediate re-fire. On success the timer is overwritten with the full schedule.

**Origin:** P0 Incident 2026-06-21 — `PeriodicJob` set timer after `_job_fn()`, so a crashing sweep never recorded its next run and retried every 5 minutes forever.

## 19. Scheduler/background-process writes share a database file with MCP writes → structural contention

When a background process (scheduler, sweep engine, periodic job) and the main MCP server both write to the **same SQLite database file**, they contend at the OS/file-system locking layer even with separate connections. `busy_timeout` mitigates the symptom (wait-and-retry) but does not remove the root cause (two processes competing for the same exclusive write lock on the same file).

```python
# BLOCKER — both write to lorekeeper.db through separate connections
db = Database(s.sqlite_path)                        # MCP writes here
sweep_db = Database(s.sqlite_path)                  # sweep ALSO writes here
sweep_svc = SweepService(conn=sweep_db.conn, ...)   # contention guaranteed

# CORRECT — sweep writes to its own database file
db = Database(s.sqlite_path)                        # MCP writes to lorekeeper.db
sweep_db = Database.apply_sweep_schema(             # sweep writes to sweep.db
    s.sweep_sqlite_path,
)
sweep_svc = SweepService(conn=sweep_db.conn, ...)   # zero contention
```

**Check:** For every background process (PeriodicJob, SweepService, or any daemon thread that performs writes), verify it writes to a **separate database file** dedicated to its workload. The pattern is:

1. Config defines the path (`sweep_sqlite_path`)
2. `Database.apply_sweep_schema()` creates the file with only the tables that process needs (no FK references to main-DB tables)
3. The process's stores (ConfigStore, LinkSuggestionStore, MetricsStore) bind to the sweep DB
4. Reads from the main database go through a separate _read-only_ connection (safe — WAL mode readers never block or get blocked)

**Origin:** P0 Incident 2026-06-21 (IR-002) — sweep wrote to `lorekeeper.db` alongside MCP. Fixed post-incident via PR #241: sweep writes to `sweep.db` exclusively.

## 20. Module-level variable assigned in init function without `global` declaration → local variable leak

Assigning a value to a module-level variable inside a function (e.g. `init_service()` in `server.py`) without declaring it `global` creates a **local variable** — Python's scoping rule. The module-level name stays `None`, so any code path that reads the module-level variable will get `None` at runtime.

```python
# BLOCKER — _suggestions_store is NOT declared global
_suggestions_store: LinkSuggestionStore | None = None

def init_service():
    global _svc                                  # ← only _svc is declared global
    _suggestions_store = LinkSuggestionStore(...) # ← creates LOCAL variable!
    ...

def get_suggestions_store() -> LinkSuggestionStore:
    assert _suggestions_store is not None         # ← always raises! value stays None
    return _suggestions_store

# CORRECT — declare ALL module-level variables as global
_suggestions_store: LinkSuggestionStore | None = None

def init_service():
    global _svc, _suggestions_store               # ← declare every one
    _suggestions_store = LinkSuggestionStore(...)
    ...
```

**Check:** For every function in `server.py` (or any handler module) that assigns to a module-level variable, read the `global` declaration at the top of the function. Every module-level name on the left side of `=` in that function must appear in a `global` statement. Not just the one you remember — **all of them**.

**Origin:** LKPR-100 (PR #246), Copilot blocker. `init_service()` only declared `global _svc`, omitting `_suggestions_store`.

## 21. Metrics increment via direct store call instead of MemoryService safe pattern

`MemoryService._increment_metric()` is the canonical write path for metrics:

- It wraps the store call in a try/except (metrics failures are best-effort — never break the MCP call)
- It performs the commit after the write
- It matches the pattern used by every other tool handler

Using `MetricsStore.increment_metric()` directly:

- Can raise `sqlite3.Error` and break the MCP tool call
- May not commit (commit depends on the caller's convention)

```python
# BLOCKER — can raise, break the call, and not commit
svc.metrics.increment_metric("lore_get_suggestions")

# CORRECT — safe, committed, best-effort
await self._increment_metric("lore_get_suggestions")
```

**Check:** Any `svc.metrics.increment_metric()` (or `svc.metrics` followed by `.commit()`) in a handler or server file. The only valid use is when the metrics write and the primary operation are part of the same batch commit — but even then, prefer `_increment_metric` to keep error handling uniform.

**Origin:** LKPR-100 (PR #246), Copilot issue flag.

## 22. Per-item exception results in partial DB writes committed → data corruption

When a batch handler processes items with per-item error handling and commits at the end, an item that raises after writing to the DB (e.g., link insert succeeds but status update fails) will have its partial writes committed even though the item is reported as errored.

```python
# BLOCKER — item A's DB writes are committed even when A is reported as errored
for sug_id in suggestion_ids:
    try:
        link_id = store.insert_link(...)   # ← succeeds
        store.update_status(sug_id, "accepted")  # ← raises!
        results.append({"id": sug_id, "status": "accepted"})
    except Exception as e:
        results.append({"id": sug_id, "status": "error", "error": str(e)})
        # ← link IS inserted but NEVER committed, because...
svc.commit()  # ← wait, actually COMMITTED — the link insert affected the buffer!
```

The problem is that `insert_link()` (a DML statement) affects the in-memory transaction buffer _immediately_. When the outer function later calls `commit()`, **all** buffer changes — including the partial success from the errored item — are committed. The caller sees `status: "error"` but the link row is persisted.

**Mitigations (use one, in order of preference):**

1. **Use SQL savepoints per item** — `SAVEPOINT item_N` / `RELEASE item_N` / `ROLLBACK TO item_N` for atomic per-item units within the outer transaction
2. **Write-phase ordering** — perform all checks/deterministic operations before any DML. Do the DML only at the end when all checks pass
3. **Two-phase** — first pass validates all items (read-only), second pass performs writes (no failures expected)

```python
# CORRECT — use savepoints for per-item atomicity
for i, sug_id in enumerate(suggestion_ids):
    try:
        conn.execute("SAVEPOINT item_?;", (i,))
        link_id = store.insert_link(...)
        store.update_status(sug_id, "accepted")
        conn.execute("RELEASE SAVEPOINT item_?;", (i,))
        results.append({"id": sug_id, "status": "accepted"})
    except Exception as e:
        conn.execute("ROLLBACK TO SAVEPOINT item_?;", (i,))
        results.append({"id": sug_id, "status": "error", "error": str(e)})
conn.commit()
```

**Check:** Any batch handler that iterates items with per-item try/except and writes to DB inside the loop while committing only once at the end. The key signal: a DB write before the last success point in the loop body.

**Origin:** LKPR-100 (PR #246), Copilot issue flag.

## 23. Read-side migration must handle direction inversion without data semantics corruption

When a migration renames a relation type whose meaning inverts the subject/object relationship (e.g., `"used_by" → "depends_on"`), a simple string replacement in the `relation_type` column is **incorrect** — the direction semantics are now reversed.

```python
# BLOCKER — changes the label but NOT the direction
def normalize_legacy_relation_type(rt: str) -> str:
    return MIGRATION_MAP.get(rt, rt)   # "used_by" → "depends_on"

# A call to normalize_legacy_relation_type("used_by") returns "depends_on"
# But old row: (A, used_by, B) meant "B uses A" = "A depends on B"
# New row: (A, depends_on, B) means "A depends on B" — CORRECT, but ONLY
# because the source and target weren't swapped... so (A, depends_on, B) reads
# "A depends on B" = (A, used_by, B) read "B uses A" — these are EQUIVALENT
# ONLY if source/target don't matter.

# ACTUAL CORRECT — swap source and target when direction inverts
def normalize_legacy_relation_type_and_direction(
    rt: str, source_id: str, target_id: str
) -> tuple[str, str, str]:
    if rt == "used_by":
        return ("depends_on", target_id, source_id)  # ← SWAP source and target
    return (MIGRATION_MAP.get(rt, rt), source_id, target_id)
```

**Check:** For every entry in a type-migration map, verify whether the new type name preserves or inverts the subject/object relationship. If it inverts, the migration must swap `source_memory_id` and `target_memory_id` for affected rows. A read-side normalization function that only returns a new string without also returning swapped IDs is a silent data semantics corruption.

**Origin:** LKPR-67 (PR #235), Copilot blocker.

## 24. Backup restore path rejects legacy data types without normalization

`import_dump()` writes the raw `relation_type` from the dump file directly into `insert_link()`. After a type migration removes old type values (e.g. `"related_to"`, `"used_in"`), the store's write-time validation rejects these — making old backup files **unrestorable**.

```python
# BLOCKER — old dumps rejected after type migration
def import_dump(data: dict) -> int:
    ...
    for link in data.get("links", []):
        link_store.insert_link(   # ← raises if link["relation_type"] was removed
            source_memory_id=...,
            target_memory_id=...,
            relation_type=link["relation_type"],  # ← raw from dump — may be "related_to"
        )
```

**Fix:** Normalize legacy types (and handle direction inversion) before calling `insert_link`:

```python
def import_dump(data: dict) -> int:
    ...
    for link in data.get("links", []):
        rt = link["relation_type"]
        norm_rt, src, tgt = normalize_legacy_relation_type_and_direction(
            rt, link["source_memory_id"], link["target_memory_id"]
        )
        link_store.insert_link(
            source_memory_id=src,
            target_memory_id=tgt,
            relation_type=norm_rt,
        )
```

**Check:** Every code path that inserts links from external/exogenous data (dump imports, backup restore, migration scripts) must normalize types through the same map used for read-side normalization. If the read-side normalizes but the write-side doesn't, backup files become a time bomb.

**Origin:** LKPR-67 (PR #235), Copilot blocker.
