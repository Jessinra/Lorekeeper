# Lorekeeper Copilot Code Review Instructions

These instructions guide Copilot (and any AI reviewer) for this repository.

---

## Review Severity Tiers

Every review comment **must** carry an explicit severity label. Unlabeled comments are unclear
and tend to be ignored.

| Tier       | Label         | Merge impact                                | When to use                                                                               |
| ---------- | ------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 🔴 BLOCKER | `blocker:`    | **Blocks merge. No exceptions.**            | Security bug, data corruption, MCP contract violation, architectural constraint violation |
| 🟠 MAJOR   | `issue:`      | Fix before merge OR create follow-up ticket | Logic error, N+1 query, missing test on critical path, blocking I/O in async              |
| 🟡 MINOR   | `suggestion:` | Fix encouraged, deferrable                  | Non-idiomatic code, weak naming, missing docstring                                        |
| 🔵 NIT     | `nit:`        | Completely optional, never blocks           | Style preference, alternative valid implementation                                        |
| ✅ PRAISE  | `praise:`     | n/a                                         | Good patterns — use actively                                                              |

**Merge contract** — a PR is mergeable when:

- ✅ All BLOCKER comments resolved
- ✅ All MAJOR comments resolved OR a follow-up ticket created
- ✅ CI gates green (lint, type check, tests, PR size)
- ✅ At least 1 human approval

---

## Conventional Comments Format

Every comment must use this format:

```
<label> [(<decorator>)] [<file>:<line>]: <subject>

[1–3 line explanation]
[Optional: code example showing the fix]
Rationale: <why this matters>
```

**Good example:**

```
blocker: (src/lorekeeper/server.py:78): print() call leaks to MCP protocol stdout.
Replace with: structlog.get_logger().info("message")
Rationale: stdout is reserved for MCP JSON-RPC. Any stray print() corrupts the protocol stream.
```

**Bad example (don't do this):**

```
This could be better.
```

---

## Lorekeeper Architecture Constraints

These are project-specific rules. Violations are **BLOCKER**-tier regardless of how minor they look.

### Core invariants

- **stdout is reserved for MCP protocol** — `print()` in any runtime file (`src/`) is a bug.
  All logging goes to stderr via `structlog`. Only intentional CLI tools are exempt.
- **`infer=False` on every `mem0.add()` call** — memories are stored verbatim.
  Any call without `infer=False` silently invokes an LLM and corrupts stored content.
- **`lore_id` (UUID) is the canonical identity** — never expose Mem0's internal id.
  Any code that leaks `mem0_id` to callers is a BLOCKER.
- **MCP API surface is stable** — tool names, input schemas, and output schemas must not
  change in a backwards-incompatible way. The existing skills rely on them.
- **Migrations are additive and idempotent** — new schema changes go into `MIGRATIONS` list
  as `(N, name, fn)` with strictly-increasing version numbers. Never modify existing migrations.

### Service layer

- All DB access goes through the store classes (`MemoryStore`, `LinkStore`, etc.),
  never direct SQL in handlers or server code.
- `MemoryService` is the orchestrator — it owns cross-store coordination.
- Transaction boundaries live in the service layer, not in stores or handlers.

### Scoring and memory logic

- Changes to hybrid scoring weights (`LORE_W_*`), duplicate threshold, or soft-delete
  trigger conditions are **high-risk** — flag them as MAJOR minimum and require tests.
- `soft_deleted=True` is irreversible at the app layer (no undelete tool). Be careful.
- Score bumps/deductions must use the EMA window pattern — not raw arithmetic.

---

## Review Priorities

Apply in this order — stop at the first BLOCKER and surface it immediately.

### 1. 🔴 Security & Data Integrity (BLOCKER tier)

- `print()` in `src/` runtime code (MCP protocol violation)
- Hardcoded secrets, API keys, tokens
- SQL injection — any f-string or `.format()` inside a `cursor.execute()` call
- Missing `infer=False` on `mem0.add()` calls
- `lore_id` / internal Mem0 id confusion in public outputs
- `pickle.loads()` or `yaml.load()` (not `safe_load`) on untrusted data
- Missing auth checks on new endpoints

### 2. 🔴 MCP Contract Violations (BLOCKER tier)

- Any rename, removal, or schema change to existing MCP tools without explicit versioning
- New `@mcp.tool` added without README documentation and `check_mcp_docs.py` update
- Response fields dropped or renamed
- Tool added but not listed in `assets/prompts/lorekeeper-agent-prompt.md`

### 3. 🟠 Correctness & Logic (MAJOR tier)

- Bare `except: pass` or `except Exception: pass` — silently swallows failures
- Blocking I/O inside `async def` (`time.sleep()`, `requests.get()`, sync file reads)
- Missing `None` checks before attribute access on Optional values
- Multi-step DB writes not wrapped in a transaction boundary
- Off-by-one errors in pagination, window sizes, or score calculations
- Race conditions in concurrent memory access

### 4. 🟠 Performance (MAJOR tier)

- N+1 queries — DB calls inside a loop
- Unbounded `queryset.all()` without pagination
- Heavy computation on the synchronous MCP request path (should be offloaded)
- Repeated embedding computation that could be cached

### 5. 🟠 Testing (MAJOR tier)

- New business logic without tests (happy path + at least one error case)
- Changes to scoring, dedup, or soft-delete without regression test
- Test assertions that only check "didn't raise" instead of checking actual output
- E2E tests added/changed but not run locally before PR (see CLAUDE.md)

### 6. 🟡 Code Quality (MINOR tier)

- Type annotations missing on public function signatures
- Functions >50 lines — flag for potential extraction
- Magic numbers not in named constants or `Settings`
- Dead code, commented-out blocks, unused imports
- Exception messages that are bare (`raise ValueError` with no message)
- `logging.error()` in except blocks — should be `logging.exception()` for full traceback

### 7. 🔵 Style (NIT tier — never block)

- Import order (handled by ruff — do not comment manually)
- Line length (handled by ruff — do not comment manually)
- Minor naming preferences when the current name is already clear

---

## Repo-Specific Red Flags

Flag these immediately regardless of tier — they usually indicate a misunderstanding of
the architecture:

- Any `print(` in `src/lorekeeper/` that isn't inside a CLI tool — this is always a bug
- `mem0.add(...)` without `infer=False` — guaranteed LLM call side effect
- Direct `conn.execute()` in handler or server code — must go through store classes
- Changes to `MIGRATIONS[0]` (the bootstrap migration) — should never be modified
- Importing from `dashboard/` in server code — wrong dependency direction
- Adding `import requests` to `server.py` or `handlers.py` — use `httpx` async
- Test that calls `asyncio.run()` directly — use `pytest-asyncio` fixtures

---

## Review Style Rules

- **Be specific** — reference exact file and line numbers (`src/lorekeeper/server.py:112`)
- **Be actionable** — show the fix, not just the problem
- **Be concise** — bullet points, not paragraphs
- **Comment only on the diff** — do not flag pre-existing issues that weren't touched
- **Acknowledge good patterns** — use `praise:` when something is done well
- **Explain the rationale** — especially for BLOCKER/MAJOR tier — "why does this matter?"
- **Prefer concrete fixes over general advice** — show code, not vague suggestions

---

## What NOT to Comment On

Automation handles these — leave them to the tools:

- Import order → ruff
- Line length, whitespace → ruff
- Type errors → mypy (check in CI)
- Coverage numbers → pytest-cov (CI enforces threshold)
- Markdown formatting → prettier (CI enforces)
- Skill format → check_skills.py (CI enforces)

If one of these appears in a PR and CI is passing, assume the author ran the tools.
