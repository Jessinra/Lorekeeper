---
id: LKPR-103
title: Codebase cleanup — remove dead ABC, extract handlers, consolidate tests
type: chore
status: S:proposal
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Diana (Jason)
filed_date: 2026-06-30
github_issue: 251
---

# [LKPR-103] Codebase cleanup — remove dead ABC, extract handlers, consolidate tests

## Problem

The codebase has accumulated three categories of friction since the June 18 ChromaDB removal refactor:

1. **Dead abstraction** — `services/memory_engine.py` (43-line ABC) + `services/engine_factory.py` (9-line shim) exist solely because we once supported ChromaDB and Mem0. There is exactly one vector backend (LanceDB). The abstract `MemoryEngine` interface, with methods like `find_vector_id`, `get_embeddings_batch`, `delete_by_vector_id`, and `get_all`, adds indirection with zero benefit. Every consumer passes through the factory shim to get a `LanceDBEngine`.

2. **Server.py is too long** — `server.py` is 850 lines mixing three concerns: boot/initialization (100 lines), handler functions with validation logic (400 lines), and MCP tool decorators (250 lines). The handler validation and business logic can't be unit-tested independently of the MCP server.

3. **Test files named by ticket number** — Five test files (`test_pr237_review_fixes.py`, `test_pr111_review_fixes.py`, `test_lkpr78_critical_coverage.py`, `test_lkpr58_link_candidate.py`, `test_lkpr60_lkpr54.py`) are named by ticket/PR number rather than the module they test. This makes test discovery follow ticket history instead of source structure, and every new ticket adds a new file instead of extending the appropriate module file.

## Solution

### 1. Remove MemoryEngine ABC + engine_factory.py

- Delete `services/memory_engine.py` (ABC + imports)
- Delete `services/engine_factory.py` (3-line shim)
- Inline `LanceDBEngine` — remove `MemoryEngine` parent, remove ABC imports
- Update type annotations in `orchestrator.py`, `link_candidate.py` to use `LanceDBEngine` directly
- Update `server.py:init_service()` to call `LanceDBEngine(...)` directly instead of `build_engine(...)`

### 2. Extract MCP handlers from server.py

- Create `src/lorekeeper/handlers.py`
- Move all `_handle_*` functions (search, insert, remember, update, reflect, forget, recommend_links, get_suggestions, review_suggestion) into `handlers.py`
- Move constants (`_VALID_SEARCH_FORMATS`, `_MAX_SUGGESTIONS_LIMIT`, `_VALID_REVIEW_ACTIONS`) alongside their handlers
- Keep module-level globals (`_svc`, `_suggestions_store`) + `get_service()`, `get_suggestions_store()`, `init_service()` in `server.py`
- `server.py` imports `_handle_*` from `handlers.py`; MCP tool decorators call them directly

### 3. Consolidate ticket-named test files

- Merge `test_lkpr58_link_candidate.py` (638 lines) → `tests/test_link_candidate.py`
- Merge `test_lkpr60_lkpr54.py` (162 lines) → `tests/test_memory_service.py`
- Merge `test_lkpr78_critical_coverage.py` (535 lines) — split: MCP backend tests → `tests/test_handlers.py`, Dashboard API tests → `tests/test_dashboard.py`
- Merge `test_pr111_review_fixes.py` (200 lines) → `tests/test_metrics_store.py`
- Merge `test_pr237_review_fixes.py` (162 lines) — sweep script test → `tests/test_sweep.py` or `tests/e2e/`
- Delete the original ticket-named files

## Acceptance Criteria

- [ ] `services/memory_engine.py` deleted — `LanceDBEngine` is the sole vector backend, no ABC in hierarchy
- [ ] `services/engine_factory.py` deleted — `server.py` constructs `LanceDBEngine` directly
- [ ] All type annotations updated: `MemoryEngine` → `LanceDBEngine` in `orchestrator.py`, `link_candidate.py`
- [ ] All tests pass after ABC removal (22+ test files unchanged)
- [ ] `src/lorekeeper/handlers.py` created with all `_handle_*` functions
- [ ] `server.py` shrinks from ~850 lines to ~450 lines (tool decorators + boot only)
- [ ] `handlers.py` functions accept `svc: MemoryService` as first param (no global dependency)
- [ ] All tests pass after handler extraction
- [ ] Ticket-named test files consolidated into module-level files
- [ ] Original ticket-named files deleted
- [ ] Full test suite green (`uv run pytest`)
- [ ] Ruff + mypy pass (`uv run ruff check src tests/`, `uv run mypy src`)

## Affected Files

### Remove

- `src/lorekeeper/services/memory_engine.py`
- `src/lorekeeper/services/engine_factory.py`
- `tests/test_pr237_review_fixes.py`
- `tests/test_pr111_review_fixes.py`
- `tests/test_lkpr78_critical_coverage.py`
- `tests/test_lkpr58_link_candidate.py`
- `tests/test_lkpr60_lkpr54.py`

### Create

- `src/lorekeeper/handlers.py` — extracted handler functions + validation

### Modify

- `src/lorekeeper/services/lancedb_engine.py` — remove ABC parent, seal class
- `src/lorekeeper/services/orchestrator.py` — use `LanceDBEngine` type annotation
- `src/lorekeeper/services/link_candidate.py` — use `LanceDBEngine` in TYPE_CHECKING
- `src/lorekeeper/server.py` — use `LanceDBEngine` directly, delegate to `handlers.py`
- `tests/test_link_store.py` — absorb `test_lkpr60_lkpr54` cache tests
- `tests/test_handlers.py` — absorb MCP handler tests from `test_lkpr78`
- `tests/test_dashboard.py` — absorb dashboard tests from `test_lkpr78`
- `tests/test_suggestion_store.py` — absorb PR #237 sweep tests
- Plus: update imports in any file referencing `MemoryEngine` or `engine_factory`

## Dependencies

None — purely mechanical refactoring, no functionality changes.

## Required Updates

- **CLAUDE.md**: [ ] Update architecture section — remove `MemoryEngine` from store list
- **Skills**: [ ] N/A
- **Backlog**: [ ] Promote to `ready/` when approved

## Notes

No behavior changes. Every step preserves exact MCP API surface. The test consolidation preserves all test coverage — no test logic is removed, only relocated.
