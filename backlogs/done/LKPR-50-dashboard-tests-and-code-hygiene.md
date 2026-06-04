---
id: LKPR-50
github_issue: 98
title: Dashboard tests, serialization unification, engine ABC cleanup, and quality gate hardening
type: chore
sprint: 2
rice_score: ~
filed_by: Diana
filed_date: 2026-05-31
---

# [LKPR-50] Dashboard tests, serialization unification, engine ABC cleanup, and quality gate hardening

## Problem

Four independent code-hygiene gaps, none urgent alone but collectively slowing development:

1. **Zero dashboard test coverage.** All 389 lines of `dashboard/app.py`, the shared `serializers.py`, and the MCP `server.py` tool definitions are untested. A data model change can silently break the dashboard — you only find out by launching it and clicking around.
2. **Duplicated serialization logic.** The `serializers.py` module exists to centralize Memory/MemoryLink/SearchResult output shaping, but `dashboard/app.py` bypasses it entirely using `dict(row)` and `lnk.model_dump()` inline. Adding a field to the Memory model requires touching both paths.
3. **`MemoryEngine` ABC doesn't match real usage.** The ABC declares `normalize_score` but ChromaDBEngine does normalization inline in `search()`. `delete_by_mem0_id` is defined but orchestrator never calls it. `find_mem0_id` exists in the test `FakeEngine` but not in the ABC. Every engine change must be implemented twice (Chroma + LanceDB) for a legacy backend that most users don't use.
4. **No type-checking enforcement.** `mypy` is configured with `strict=true` in `pyproject.toml` but never run. There are already `# type: ignore[union-attr]` comments papering over real issues.

## Solution

Group all four under one ticket with a strict ordering: **tests first**, then cleanups against the test net.

### Execution order

| Step | What | Verifies |
|------|------|----------|
| 1 | Dashboard route integration tests + `serializers.py` tests + MCP server tests | Test suite covers all untested paths |
| 2 | Dashboard → use `serializers.py`, remove `window.*` JS globals from `api.js` | Existing tests pass, no behavioral change |
| 3 | Config override type validation at `PATCH /api/config` | Invalid types return 422 instead of crashing on next search |
| 4 | Clean up `MemoryEngine` ABC — remove unused methods, add `find_mem0_id` | Interface matches usage, tests conform |
| 5 | Run `mypy src` as non-blocking pre-commit advisory, fix existing issues | Type issues surfaced, pre-commit is future-compatible |

Steps 2–4 each touch different files — no merge conflicts.

## Acceptance Criteria

- [ ] **Step 1 (tests):** Integration tests cover all dashboard routes (`/api/memories`, `/api/links`, `/api/search`, `/api/config`, `/api/export`, `/api/import/*`, `/api/sessions`, `/api/reflections`, `/api/metrics`). Integration tests cover `serializers.py` all three functions. MCP server error paths are tested (missing `refine_from` cap, missing title in lore_insert).
- [ ] **Step 2 (dashboard cleanup):** All dashboard routes use `serializers.serialize_memory()` or `serialize_search_result()` — no `dict(row)` or `lnk.model_dump()` inline. `window.api` and `window.showToast` removed from `api.js` — all consumers use ES module imports.
- [ ] **Step 3 (config validation):** `PATCH /api/config` rejects overrides with wrong types at set time (e.g., string for `w_semantic`) — returns 422 with error detail.
- [ ] **Step 4 (engine ABC):** `MemoryEngine` interface matches actual usage across orchestrator + dashboard + scripts. `find_mem0_id` added to ABC + both engine implementations. `normalize_score` is actually called by callers, not used inline.
- [ ] **Step 5 (mypy):** `mypy src` runs in pre-commit (non-blocking advisory). Existing `type: ignore` comments reviewed and resolved where possible.

## Affected Files

### Backend
- `src/lorekeeper/services/memory_engine.py` — update ABC (step 4)
- `src/lorekeeper/services/lancedb_engine.py` — implement `find_mem0_id`, audit `normalize_score` usage (step 4)
- `src/lorekeeper/services/chromadb_engine.py` — implement `find_mem0_id`, fix inline normalization (step 4)
- `src/lorekeeper/serializers.py` — ensure coverage (step 1)
- `src/lorekeeper/server.py` — add error-path tests (step 1)

### Dashboard
- `src/lorekeeper/dashboard/app.py` — use serializers module, validate config types (steps 2–3)
- `src/lorekeeper/dashboard/static/js/api.js` — remove `window.*` assignments (step 2)

### Tests
- `tests/test_serializers.py` — new file or extend existing (step 1)
- `tests/test_dashboard.py` — new file for FastAPI TestClient integration tests (step 1)

### Config / CI
- `.githooks/pre-commit` — add mypy advisory (step 5)
- `pyproject.toml` — minor config adjustments if needed (step 5)

## Dependencies

- **LKPR-45**: Step 2's `window.*` removal is the final cleanup from LKPR-45's tab-registry refactor. LKPR-45 must be merged first (the core work is done on main, but the ticket is still `S:ready` — update status if needed).

## Required Updates

- **CLAUDE.md**: [ ] Update if mypy advisory is added to pre-commit workflow section
- **README.md**: [ ] N/A
- **Skills**: [ ] Update `lorekeeper-dev` skill with new pre-commit behavior
- **Backlog**: [ ] Move LKPR-45 to `S:done` once its window.* cleanup is included here

## Open Questions

_None_

## Notes

**Why one ticket instead of five:** The four workstreams are independent (no file overlap, no ordering constraint except tests-first). Splitting would add PR overhead with no benefit. Combined, it's ~500 lines changed across ~15 files — medium PR.

**Why P1:** The dashboard test gap is a real risk — data model changes land silently. Everything else in this ticket is P2/P3 individually, but bundling with the test net makes it worth scheduling now.

**Not in scope — LinkStore splitting (LKPR-50+1):** The LinkStore god object (637 lines) is a larger refactor that needs its own ticket with a plan. This ticket focuses on the smaller, testable gaps.
