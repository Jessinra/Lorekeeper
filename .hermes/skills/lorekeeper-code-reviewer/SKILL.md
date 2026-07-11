---
name: lorekeeper-code-reviewer
description: "Lorekeeper-specific BLOCKER patterns, severity tiers, and review checklist — used when reviewing any PR touching src/lorekeeper/"
version: 1.19.0
author: Diana
---

# Lorekeeper Code Review Patterns

Use this skill when reviewing any PR that changes `src/lorekeeper/` runtime code, services, handlers, or MCP server. These are project-specific patterns that general-purpose review prompts miss.

**Incident-driven:** BLOCKER patterns 16-19 added after P0 Incident 2026-06-21 (Lorekeeper SQLite lock contention + infinite retry storm). See `docs/incidents/IR-002-lorekeeper-sqlite-lock-contention.md`. Patterns 20-24 added after LKPR-100 (server wiring, metrics, partial commits) and LKPR-67 (type migration, backup compatibility).

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

## How to Use This Skill

1. **Holistic review** — Before checking the diff, read every changed file in full, read adjacent files (server.py wiring, caller modules), and read the ticket/plan. Does the implementation match the design? Does the new code belong where it was placed? This catches the most expensive class of bugs: architectural misalignment. Load `references/holistic-review.md` for the full framework.
2. **Pre-check** — `git diff main...HEAD --name-only | grep -q "^src/lorekeeper/"` → RUNTIME or NON-CODE
3. **Deleted-file check** — `git diff main --name-status --diff-filter=D | grep -q "^D"` — any deleted test file is BLOCKER unless replaced. Any deleted source file without a rename/move justification is BLOCKER.
4. **API divergence check** — compare MCP tool signatures in `server.py` against the ticket ACs. A different param name, type, or arity is a BLOCKER that requires PM sign-off.
   4a. **Required-updates check** — scan the ticket's "Required Updates" section and every `- [ ]` AC checkbox for explicit skill/doc/script update obligations. A checkbox is a contract: if it's not in the diff, it's a missed AC regardless of whether the feature code works. LKPR-100 example: AC said "`lorekeeper-reconcile` — note suggestion review workflow" — if the diff doesn't touch that skill, it's a MAJOR miss.
5. **RUNTIME PR** → load `references/blocker-patterns.md` for the 24 BLOCKER patterns
6. **NON-CODE PR** → load `references/non-code-pr-checklist.md` instead
7. **All PRs** → check Maintainability (`references/maintainability-simplicity.md`)
8. **Migration PRs** → check Backward Compatibility (`references/backward-compatibility.md`)
9. **README / user-facing docs** — `README.md` is the docsite homepage. Spot-check for:
   - Duplicate or conflicting sections (Performance, Configuration, etc.)
   - Stale dates ("Last verified")
   - Content relevant to users (agents), not internal developers
   - Env var tables that list internal config instead of user-relevant vars
   - Broken or orphaned code fences from PR merge artifacts
10. **Pre-merge** → run `references/pre-deployment-checklist.md`

## 🟠 MAJOR Review Priorities

### Architecture & Holistic Fit (BLOCKER if wrong)

### BLOCKER — Test file deleted with no replacement

**Check:** `git diff main --name-only --diff-filter=D | grep "tests/"` — any deleted test file is a presumptive BLOCKER.

**Why:** deleted test files silently remove coverage for ALL paths they exercised, not just the ones the PR changed. In LKPR-100, `tests/test_handlers.py` was deleted (499 lines, 40 tests), eliminating coverage for every pre-existing MCP handler. The new `test_suggestion_store.py` only covered store-level tests.

**Check sequence:**

1. `git show main:<deleted-file> | grep -c "def test_"` — count deleted test functions
2. `git diff main --name-only --diff-filter=A | grep "tests/"` — count replacement files added
3. Deleted count >> replacement count = BLOCKER regardless of whether the PR's own feature is tested

**Resolution:** restore the deleted file and add the new test class alongside. Deleting and replacing is never safe — any test file refactor must preserve every pre-existing test function.

**Not checking the diff first** — check the whole system first. This is the single most important review discipline.

- **Read every changed file in full**, not just the diff. The diff shows what changed; the full file shows what stayed and why.
- **Read adjacent files** — how is the new code wired in `server.py`? How do callers reach it? If the only callers are tests, the production path is dead code.
- **Does it belong here?** — is this a user-facing operation (MemoryService) or a background task (standalone service)? A new method on a god class that could be a standalone module is a BLOCKER.
- **Is it the simplest version?** — premature abstraction (configurable weights never tuned, ABCs with one subclass, factories with one product) is complexity debt. Delete the abstraction and see if the code is simpler.
- **Read the ticket/plan** — does the implementation match what the ticket describes? PR #237's ticket said `MemoryService.sweep_links()` but the code defined `SweepService.run()` — a stale description that confused reviewers.
- **Trace every constructor parameter** — if `__init__` stores `self.X = x`, every method body must reference `self.X`. An unused parameter is dead code (see the `db: Database` regression in PR #237).
- **Architecture over diff** — a perfect diff that's wired into the wrong layer is a worse outcome than a messy diff in the right place. Architectural misalignment is a BLOCKER.

See `references/holistic-review.md` for the full framework and checklist.

### Filter validators must catch `(ValueError, TypeError)`

```python
# MAJOR — datetime.fromisoformat() raises TypeError on non-string input
def parse_filter_dt(value: str, field_name: str) -> datetime:
    try:
        return parse_iso_utc(value)
    except ValueError as exc:  # ← misses TypeError!
        raise ValueError(...)
```

Functions that call `datetime.fromisoformat()` must wrap `(ValueError, TypeError)`.

### Private-to-public alias refactors

When a PR renames a private symbol to public (`_parse_iso_utc` → `parse_iso_utc`), grep every module that imported the old name — remaining private-name imports make the code harder to trace.

### Model field types use Literal alias, not bare `str`

```python
# MAJOR
class Memory(BaseModel):
    source_type: str = "observed"

# CORRECT — Pydantic + mypy enforce at construction
class Memory(BaseModel):
    source_type: SourceType = "observed"
```

### Correctness & performance

- Missing `None` checks before attribute access on Optional values
- Multi-step DB writes not wrapped in a transaction
- Off-by-one in pagination, window sizes, score calculations
- N+1 queries — DB calls inside a loop
- Unbounded `.all()` / `.fetchall()` without pagination
- **Non-atomic write ordering** — vector-store operation (e.g. `_engine.add()`) before the corresponding DB row is durably committed creates orphaned vector entries if the DB write fails. Reorder: DB write → commit → vector write, or use a two-phase approach. PR #262 (LKPR-104 Phase 5).
- **Logging authoring data on error paths** — `logger.warning("Auto-insert failed", text=str(text)[:80])` exposes factual discoveries or lessons in stderr logs. Any log message that includes partial memory text (title, description, content) on auto-insert/reflection/submission failures is a security exposure. Log the `lore_id` or a hash, not the authoring text. PR #262 (LKPR-104 Phase 5).
- **Transaction boundary in route/handler layer** — `db.conn.commit()` calls inside route handlers or MCP handler functions instead of in domain services/processors. Handlers should orchestrate; they should not own the commit boundary. If a route handler issues `commit()`, the operation's atomicity depends on the handler layer — which is neither tested nor guaranteed across handler reorganisation. Delegate commit ownership to the service/processor layer. PR #279 (LKPR-105 Step 5).

### README / user-facing docs (docsite homepage)

`README.md` is included in the docsite as `docs/index.md`. A broken README is a broken homepage.

- **Duplicate sections** — `## Performance` appearing twice, conflicting or stale content. If benchmark data exists, remove the "coming soon" placeholder.
- **Env var tables** must list user-relevant vars (`LORE_DATA_DIR`, `LORE_NAMESPACE`, `LORE_SEARCH_LIMIT`, `LORE_LINK_TOP_M`), not internal configuration (`LORE_SUGGEST_*` sweep settings, scorer weights). Internal vars belong in `config.py` / `CLAUDE.md`.
- **No developer noise** — Setup (Git clone), Development, Project Layout, pre-commit hooks, and CI commands belong in docs or CLAUDE.md, not the user-facing README.
- **No merge artifacts** — orphaned code fences, split directory trees, sections that appear under the wrong heading (e.g. a Configuration section embedded inside Project Layout).
- **Stale "Last verified" date** — update to current date.
- **Relative links to docsite pages** must use absolute GitHub blob URLs so they work on both GitHub and the docsite (see lorekeeper-dev reference).

### Testing

- **Deleted test files in `git diff --name-only`** — a `D tests/test_*.py` entry is BLOCKER-tier. Deleting a test file without a replacement removes all coverage that was in it. Run `git diff main --name-only | grep "^D.*test_"` explicitly during review to catch this. Also check that the new test count is net-positive (not just "tests exist").
- New business logic without tests (happy path + ≥1 error case)
- **New scripts/ entrypoints** — add a subprocess regression test (`subprocess.run`) that exercises both `--dry-run` and real-run paths against a temp database. PR #237's `scripts/sweep-links.py` crashed on its default path because it called a method that didn't exist. A smoke test would have caught it.
- Changes to scoring, dedup, soft-delete without regression tests
- Tests that check "didn't raise" instead of actual output
- E2E tests changed but not run locally before PR
- New test files not lint-checked — `ruff check tests/`

### Dead instance attributes

Cross-reference `self.X =` in `__init__` vs all method bodies. ruff does NOT flag unused instance attributes.

### Deferred imports inside loops

Any `from X import Y` inside a `for` loop body is a smell. Python caches module lookups so it won't re-execute module code, but the import lookup itself runs on every iteration. For batch tools (e.g. `lore_review_suggestion` processing N suggestion IDs), this multiplies needlessly. If the symbol is already importable at module level, move it there.

Pattern to catch:

```python
for item in batch:
    from some.module import CONSTANT   # ← runs N times; should be module-level
    if value not in CONSTANT:
```

**Real example (LKPR-100, `server.py:667`):** `from lorekeeper.models import RELATION_TYPES` inside the per-item accept loop — `RELATION_TYPES` was already importable at the top of `server.py`. One-line fix: add to the module-level import.

### Redundant method pairs in store classes

When a PR adds a parameterized query method to a store (`get_pending_suggestions(limit, min_score)`) and a simpler version of the same query already exists (`all_pending_suggestions()`), flag the older method as dead code per Jason's explicit principle: remove unused infra rather than keeping it "for future use". Check `grep -rn "all_pending_suggestions" src/ tests/` to confirm callers. If the only callers are tests, migrate them and delete the method.

### `TYPE_CHECKING`-only imports in serializers

`if TYPE_CHECKING: from X import Y` + `from __future__ import annotations` is safe for pure serializers (no `isinstance` calls). This pattern is consistent in the Lorekeeper codebase. Do NOT flag as a blocker unless an `isinstance` check or runtime attribute access requires the concrete type. Flag as `nit:` when it creates a footgun for future contributors.

- `lore_review_suggestion` returns `status` per item as one of `"accepted"`, `"rejected"`, `"skipped"`, **or `"error"`** — the last value is produced when a per-item exception is caught and swallowed. If API docs / docstrings only list the first three, flag as a `suggestion:` — callers checking `results[*].status` will get unexpected values.
- `errors` list and `results[*].status == "error"` are redundant — both are populated for failed items. Docs must reflect this dual-reporting or callers will miscount.

### Alternative paths missing side effects

When a PR adds a fast path (e.g. `ids` bulk-lookup that skips search pipeline), verify it still fires metrics, usage_count bump, cache invalidation — same as the main path.

### Facade delegation methods must preserve exact type signatures

When a refactoring PR extracts logic into domain services and leaves an orchestrator facade that delegates via `*args: Any, **kwargs: Any`, this destroys mypy/introspection coverage and risks MCP schema drift:

```python
# MAJOR — hides real signature; callers lose type checking for ALL params
class MemoryService:
    def search(self, *args: Any, **kwargs: Any) -> list[Any]:  # ← was `def search(self, query, limit=5, ...) -> list[SearchResult]`
        return self.search_service.search(*args, **kwargs)

# CORRECT — mirror the exact signature of the underlying service method
class MemoryService:
    def search(self, query: str, limit: int = 5, ..., include_links: bool = True) -> list[SearchResult]:
        return self.search_service.search(query, limit=limit, ..., include_links=include_links)
```

**Why it matters:** MCP tool schemas in FastMCP are derived from function annotations. If the facade uses `*args/**kwargs`, the MCP tool's schema drops all meaningful parameters — making the tool unusable from the client. Also, callers get no editor autocomplete or mypy validation on any kwarg.

**Check sequence when reviewing a facade/extraction PR:**

1. Does the facade expose the same public method names as the original?
2. Do the signatures still carry the full parameter list with types?
3. Are return types precise (not `list[Any]`)?
4. If the facade is temporary (scheduled for removal in a later phase), add a docstring or comment noting the expiration: `"""Temporary — delegates to service; will be inlined in Phase N."""`

**Real example (PR #262, Phase 5, July 2026):** `MemoryService.search()`, `search_by_ids()`, `insert()`, `remember()`, `update()`, `forget()`, `submit_reflection()`, and `insert_links()` all became `*args/**kwargs` wrappers. CodeRabbit and Copilot both flagged it: mypy couldn't validate any call site using the facade. Fix: each delegation method was restored to the full original signature with named parameter forwarding.

**Exception:** `recommend_links` preserved a precise return type (`list[dict[str, Any]]`) — it's the only method that kept its contract. If only one or two methods need the facade, keep explicit signatures for all of them, not just the most visible one.

### Backlog / ticket spec drift from implementation

The backlog ticket or plan document is the spec. When implementation diverges (new params, extra return values, different error handling), the backlog must be updated too — not just the code and docs.

**Check sequence:**

1. Read the ticket's Status examples, response schemas, and Required Updates list
2. Trace every `status` string literal the handler actually emits on `results[*]`
3. If runtime emits `"error"` but ticket examples only list `accepted/rejected/skipped`, that's a MAJOR gap — agents reading the ticket will write code that doesn't handle all branches
4. If ticket references nonexistent files (e.g. `schemas.py`), that's a MINOR issue in the ticket itself — flag and fix

**Real example (LKPR-100):** Backlog example showed `status: "accepted"` / `"rejected"` / `"skipped"` but runtime also returns `"error"`. Docs and ticket both needed updating.

### Rejecting an already-accepted suggestion must be idempotent

When `lore_review_suggestion` processes a reject action on a suggestion whose status is already `"accepted"`, the handler must treat it as a no-op (`skipped`) — not flip the status to `"rejected"`. An accepted suggestion may already have a real `memory_links` row created; reversing the status without removing the link creates an inconsistent audit trail and confuses future sweep logic.

**Check:** For every state transition in a batch handler, consider the idempotency of each action on each possible current state. If action=X on state=Y is inconsistent, define the expected behaviour (skip/error) and verify the code matches.

### Migration idempotency — safe to run twice

Every migration script (`scripts/migrate-*.py`) must be idempotent: running it twice produces the same result as running it once. The primary failure mode is `INSERT INTO ... SELECT ... WHERE` without a guard, which inserts duplicates on the second run. The migration code in `Database.migrate()` guards versioned SQL via `_schema_version` — ensure scripts also guard via `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`, `UPDATE ... WHERE condition`, or similar.

**Check:** For every new migration script, trace the control flow: what happens if the `WHERE` clause matches zero rows on the second run? If the answer is "inserts/tries again", it's not idempotent.

## 🟡 MINOR Items

- Type annotations missing on public function signatures
- Per-item `commit()` inside a batch loop — prefer a single post-loop `if wrote: svc._conn.commit()`. Per-item commits work but hold the write lock longer and cost one fsync each. Only use per-item when concurrent visibility between items is required (rare in MCP handlers).
- Functions >50 lines — flag for potential extraction
- Magic numbers not in named constants or `Settings`
- Dead code, commented-out blocks, unused imports
- `logging.error()` should be `logging.exception()` in except blocks

## Dashboard V2 (Svelte 5) — Hardcoded Value Check

**Scope:** `src/dashboard_v2/` Svelte 5 components with Tailwind v4 + CSS variables.

**Principle:** Extract a value into `primitives.ts` or `@theme` only when it serves a real purpose:

1. **Shared across components** — same value used in 2+ places (e.g. `padding-inline: 10px` in ScorePill, RelationPill, and FilterChip → extract to a shared constant or `@theme` token)
2. **Consistency anchor** — a value that defines the design system's identity (e.g. brand purple, border-radius for pills, font-size for stat values)
3. **Configurable at runtime** — a value a consumer might want to override (e.g. `HEATMAP_DEFAULTS.cellSize`)

**❌ DON'T extract:**

- One-off values unique to a single component — a Tailwind class (`h-7`) or `<style>` rule is fine
- Just because it's a "magic number" — a 28px stat value that only StatTile uses is not a problem
- Prematurely — if you're unsure, leave it inline. The cost of extracting later is trivial

**Check sequence when reviewing dashboard_v2 changes:**

1. `rg -n --glob '*.svelte' 'font-size:|font-weight:|padding-inline:|padding:' src/dashboard_v2/src/components | rg -v 'var\(|transition'` — find values in `<style>` blocks
2. For each match, ask: **"Is this value used in more than one component?"** If yes, it should be a `@theme` token. If no, leave it.
3. `rg -n --glob '*.svelte' 'px-3.*py-1|h-7|h-2|w-2|py-1\.5' src/dashboard_v2/src/components` — find Tailwind class literals that repeat across components
4. For each match, ask: **"Would changing this value require changing multiple components?"** If yes, extract to a constant. If no, leave it.
5. Cross-reference `primitives.ts` for existing `*_DEFAULTS` objects — if a new component shares the same dimension pattern (e.g. another pill component), add to the existing group, don't create a new one-off

**Key question for every hardcoded value:** _"If the designer changes this value tomorrow, how many files do I need to touch?"_

- **1 file** → fine, leave it inline
- **2+ files** → extract to a shared constant or `@theme` token

## 🔵 NIT — Never Block

- Import order → ruff
- Line length → ruff
- Type errors → mypy (CI)
- Coverage → pytest-cov (CI)
- Markdown formatting → prettier (CI)

## Lorekeeper Architecture: MemoryService vs SweepService Boundary

`MemoryService` (orchestrator) owns user-facing MCP operations. `SweepService` owns background batch operations and their stores. These are separate ownership domains. Specifically:

- `LinkSuggestionStore` belongs on `SweepService`, **not** `MemoryService`. PR #237 regression test (`test_memory_service_has_no_suggestions_attr`) guards this boundary.
- If a ticket's "Affected Files" list puts store methods on the wrong layer (e.g., puts suggestion methods on `link_store.py` instead of `suggestion_store.py`), the plan must correct it — not implement it literally.
- When a ticket's API spec and the plan differ (e.g., `suggestion_id: str` vs `suggestion_ids: list[str]`), the divergence is BLOCKER — needs PM sign-off before shipping. A different public API shape than what was specced breaks existing callers.

---

## Repo-Specific Red Flags

Flag immediately — indicate misunderstanding of the architecture:

- Any `print(` in `src/lorekeeper/` not inside a CLI tool
- `mem0.add(...)` without `infer=False`
- Direct `conn.execute()` in handler or server code
- Changes to `MIGRATIONS[0]`
- Importing from `dashboard/` in server code (wrong dep direction)
- Adding `import requests` to `server.py` — use `httpx` async
- Gitlink entry (mode 160000) without `.gitmodules` — `git rm --cached <dirname>`
- `tests/e2e/conftest.py` not updated after dependency removal
- Passing `MemoryService` (orchestrator) where a specific store/dependency type (`ConfigStore`, `Database`, `LinkStore`) is expected — `svc.config` vs `svc` confusion in PeriodicJob wiring
- Public method defined on orchestrator with identical logic to a standalone service class, but only the standalone path is wired in `server.py` (dead code duplication)
- `conn.execute(INSERT/UPDATE/DELETE)` without `conn.commit()` in the same function
- Background thread performing writes on the same DB connection as the main thread
- PeriodicJob or any scheduler setting next-run timestamp AFTER the job callback
- Background process writing to the same `.db` file as the MCP server — fix by splitting into separate database files (`lorekeeper.db` for MCP, `sweep.db` for sweep)
- `LinkSuggestionStore` or any sweep-owned store added as `self.suggestions` on `MemoryService` — the regression test `test_memory_service_has_no_suggestions_attr` catches this; if it fails, it's a blocker
- Sweep engine logic defined as a method on `MemoryService` instead of a standalone service module — Jessinra explicitly flagged this as wrong layering (PR #237)
- Module-level variable assignment inside `init_service()` / `init_*()` without corresponding `global` declaration — creates a local variable; module-level name stays `None`
- Raw `MetricsStore.increment_metric()` call in handler code instead of `MemoryService._increment_metric()` — breaks on exception, may not commit
- Batch handler looping over items with per-item try/except and committing once at the end — partial writes from errored items persist silently
- Reject or accept action that doesn't handle idempotency (flipping already-accepted to rejected, or already-rejected to accepted)
- Backup/dump restore path that doesn't normalize legacy data types — old backups become unrestorable after type migrations

## Review Style Rules

- Reference exact file:line (`server.py:112`)
- Show the fix, not just the problem
- Bullet points, not paragraphs
- **Comment only on the diff** — don't flag pre-existing issues
- Use `praise:` when something is done well
- Always explain rationale for BLOCKER/MAJOR items
- Verify local file state before reviewing — clean up any accidental local edits first, but leave PR deletions intact

## What NOT to Comment On (automation handles)

- Import order → ruff
- Line length, whitespace → ruff
- Type errors → mypy (CI)
- Coverage → pytest-cov (CI)
- Markdown formatting → prettier (CI)
- Skill format → check_skills.py (CI)

## References

| File                                       | Content                                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `references/blocker-patterns.md`           | 24 BLOCKER patterns (runtime PRs)                                                                       |
| `references/non-code-pr-checklist.md`      | Checklist for docs/CI/landing PRs                                                                       |
| `references/maintainability-simplicity.md` | Maintainability & simplicity — BLOCKER tier                                                             |
| `references/backward-compatibility.md`     | Backward compatibility — BLOCKER tier                                                                   |
| `references/pre-deployment-checklist.md`   | 30-item pre-merge checklist                                                                             |
| `references/visual-browser-review.md`      | Static site review approach                                                                             |
| `references/holistic-review.md`            | Full holistic review framework — before the diff, architecture, boundaries                              |
| `references/pr-237-review-patterns.md`     | PR #237 (LKPR-99) — script crash, dead store, README drift (real example)                               |
| `references/pr-246-review-patterns.md`     | PR #246 (LKPR-100) — deferred loop import, redundant method pair, missed AC skill update (real example) |
| `references/stale-reviewer-comments.md`    | Stale comments from new reviewers on multi-round PRs — triage pattern with PR #247 real example         |

## Python-Specific Code Smells to Catch

These patterns surface repeatedly in Lorekeeper PRs and are easy to miss in a top-level diff scan.

### Deferred import inside a loop body

```python
# BAD — re-executes the import dict lookup on every iteration
for item in items:
    from lorekeeper.models import RELATION_TYPES
    ...

# GOOD — module-level import
from lorekeeper.models import RELATION_TYPES

for item in items:
    ...
```

Python caches modules so the module body won't re-execute, but the `sys.modules` dict lookup runs every iteration. In a batch of 100 items that's 100 unnecessary lookups. More critically: errors during import surface inside the loop with a confusing traceback. Always move to module level. Check any import inside a `for`, `while`, or comprehension.

### Redundant method superseded by a more general one

When a PR adds `get_pending_suggestions(limit, min_score)` as a strict superset of `all_pending_suggestions()` (same query, no extra params), the old method is dead code. **The same PR must:**

1. Migrate every callsite (`grep -rn 'all_pending_suggestions' src/ tests/`)
2. Delete the old method

If the old method is only in tests, it's still dead — migrate and delete. Keeping "for compatibility" violates Jason's explicit lean preference. See `references/python-code-smells.md` for the full pattern catalog (to be added).

### Response schema completeness — undocumented status values

When a handler appends `{"status": "error", ...}` to `results[]` for failed items (in addition to `errors[]`), that `"error"` value **must appear in the docstring Returns union and in `docs/api-reference.md`**. Check:

- Every string literal assigned to a `status` key in the handler
- The corresponding Returns docstring
- The api-reference.md section for that tool

A caller iterating `results[*].status` and not checking `errors[]` silently misses failures if `"error"` is undocumented.

### Serializer omission of documented response fields

When the API reference / `docs/api-reference.md` documents a field in a tool's response schema, but the serializer `serialize_*()` function omits that field from its output dict, callers reading the docs will write code that expects the field — and get `undefined` at runtime.

```python
# MAJOR — serializer drops a field documented in api-reference.md
def serialize_suggestion(sug: LinkSuggestion) -> dict[str, Any]:
    return {
        "id": str(sug.id),
        "source_memory_id": sug.source_memory_id,
        # "status" is missing — documented in api-reference.md lore_get_suggestions response
    }

# CORRECT — serializer includes all documented response fields
def serialize_suggestion(sug: LinkSuggestion) -> dict[str, Any]:
    return {
        "id": str(sug.id),
        "source_memory_id": sug.source_memory_id,
        "status": sug.status,  # matches api-reference.md
    }
```

**Check sequence:**

1. Read `docs/api-reference.md` for the tool's response schema
2. Cross-reference every documented field against the serializer's output dict keys
3. Any field in docs but absent from the serializer is a MAJOR gap

**Real example (LKPR-100, PR #246):** `serialize_suggestion()` omitted the `status` field, but `docs/api-reference.md` listed it as part of `lore_get_suggestions` response. Callers iterating the response couldn't read `item.status`.

### Testing completeness — assert primary side-effects, not just status changes

When testing an endpoint whose primary side-effect is creating/modifying DB rows, the test must assert that the side-effect actually occurred — not just that the API returned a success status.

```python
# MAJOR — only checks secondary status, not primary side-effect
def test_batch_accept(suggestion_client):
    resp = suggestion_client.post("/api/suggestions/batch-review", json={...})
    assert resp.status_code == 200
    # Never checks that memory_links rows were actually created!

# CORRECT — verifies link creation, the main reason accept exists
def test_batch_accept(suggestion_client):
    resp = suggestion_client.post("/api/suggestions/batch-review", json={...})
    assert resp.status_code == 200
    links = svc.links.get_links_for_memory("mem-a")
    assert len(links) == 2  # primary side-effect verified
```

**Check sequence:**

1. Identify the endpoint's primary side-effect (create links, update scores, insert rows)
2. For accept/review endpoints: verify link creation directly via store method
3. For delete/forget endpoints: verify the row is soft-deleted or removed
4. For config endpoints: verify the config value changed via `get_override()`

**Real example (LKPR-101, PR #247):** Batch accept test checked HTTP 200 and suggestion status updates but never queried `memory_links` to verify links were actually created. Copilot flagged as issue: "the endpoint's main side-effect on accept is inserting real memory_links rows."

### Front-end batch action must not hide per-item failures

When a batch review endpoint returns per-item results (some succeeded, some errored), the front-end batch handler must only remove rows that were confirmed successful — not all selected rows.

```javascript
// MAJOR — removes all selected rows even when some failed
_batchAction() {
    const checked = [...document.querySelectorAll("#suggestions-rows .row-checkbox:checked")];
    fetch("/api/suggestions/batch-review", { method: "POST", body: JSON.stringify({...}) })
        .then(r => r.json())
        .then(result => {
            checked.forEach(cb => cb.closest("tr").remove());  // ← removes failed rows too!
        });
}

// CORRECT — only removes rows confirmed successful
_batchAction() {
    const checked = [...document.querySelectorAll("#suggestions-rows .row-checkbox:checked")];
    fetch("/api/suggestions/batch-review", { method: "POST", body: JSON.stringify({...}) })
        .then(r => r.json())
        .then(result => {
            const okIds = new Set(
                result.results.filter(r => r.status === "accepted" || r.status === "rejected").map(r => r.id)
            );
            checked.forEach(cb => {
                const row = cb.closest("tr");
                const id = row.dataset.suggestionId;
                if (okIds.has(id)) {
                    row.remove();                       // only confirmed successes
                } else {
                    cb.checked = false;
                    row.classList.remove("fade-out");   // restore failed items
                }
            });
        });
}
```

**Check:** Any batch action handler in JS that iterates over checked checkboxes and removes them without filtering by the API's per-item status. The key signal: `forEach(cb => cb.closest("tr").remove())` without a guard condition.

**Real example (LKPR-101, PR #247):** `_batchAction()` in `suggestions.js` removed all checked rows after the API call, even when the backend returned per-item errors. Users would see failed items disappear and never know to retry.

### AC completeness — Required Updates section

The ticket's `## Required Updates` section often lists skill files (e.g. `lorekeeper-reconcile`) and doc pages alongside code files. **These are AC items, not suggestions.** Before scoring the PR:

1. Read the full `## Required Updates` section of the ticket
2. Confirm every listed file was actually changed in the diff
3. If a skill file is listed but absent from the diff, that is an AC miss — MAJOR severity

## Evaluating a New / Unfamiliar Reviewer Tool

When Jason adds a new reviewer (Copilot, external bot, fresh model pass) to an already-active PR that has multiple fix commits, assess its output before acting:

**Signal:** a reviewer that doesn't have visibility into prior fix commits will surface many stale comments.

### Assessment workflow

1. **Fetch all new comments in batch** — `gh api repos/Jessinra/Lorekeeper/pulls/<N>/comments --jq '.[].body'`
2. **For every `blocker:` or `issue:` comment**, locate the exact line in the _current file_ (not the diff it was posted on). If the described bug is already gone, mark it **STALE** — no code change needed.
3. **For every `suggestion:`**, same check — if already present, mark stale.
4. **Tally signal/noise ratio** — from PR #247's new reviewer pass: 8 comments, 7 stale, 1 real (atomicity gap). A 12% hit rate is typical for a reviewer that didn't see commits `7a77d9e`+`8ee6b4b`.
5. **Reply on every comment regardless** — don't skip stale ones. Explicit replies keep the thread clean and show each item was considered. See `lorekeeper-dev-workflow` reply template.

### What "stale" means

- The exact code the comment references no longer exists at that line.
- The described bug was addressed in an earlier commit on the same branch.
- The comment cites a "last run inferred from next run" pattern that was never in the code.

### What's still valid despite staleness

- The reviewer catching a gap the prior commits _should_ have addressed but didn't (e.g. SAVEPOINT atomicity in the dashboard route vs. the MCP handler).
- Any comment about behaviour that's structurally identical even after surrounding code changed.

**Heuristic:** if ≥ 50% of a new reviewer's comments are stale, its input is still worth scanning once — the few real catches (like atomicity) are high-value — but don't treat it as a reliable gating reviewer without per-comment triage.

## Related Skills

- **[lorekeeper-qa-verification]** — Pre-deployment QA: state capture, migration integrity, MCP functional checks, DB integrity
- **[github-code-review]** — General code review process
- **[code-review-pipeline]** — Full AI-first automated pipeline
- **[requesting-code-review]** — Pre-commit quality gates
- **[lorekeeper-dev]** — Engineering workflows and pitfalls
