# LKPR-103 Implementation Plan — Codebase Cleanup

**Ticket:** LKPR-103 — Codebase cleanup (remove dead ABC, extract handlers, consolidate tests)
**Date:** 2026-06-30
**Filed by:** Diana

---

## Problem

Three layers of accumulated friction:

1. Dead `MemoryEngine` ABC + `engine_factory.py` from the ChromaDB era — 52 lines of dead indirection
2. `server.py` at 850 lines mixing boot logic, handlers, and MCP registrations — impossible to unit-test handlers independently
3. Five test files named by ticket/PR number instead of module — test discovery follows ticket history, not code structure

---

## What We're Building

Three mechanical refactors, no behavior changes:

| #   | Refactor                        | Lines removed | Lines added      | Net     |
| --- | ------------------------------- | ------------- | ---------------- | ------- |
| 1   | Remove ABC + factory            | 52            | ~0 (inline)      | **-52** |
| 2   | Extract handlers from server.py | ~400 (moved)  | ~400 (new file)  | **0**   |
| 3   | Consolidate test files          | 5 files       | 5 files (merged) | **0**   |

---

## Affected Files

### Remove (delete)

- `src/lorekeeper/services/memory_engine.py` — ABC dead
- `src/lorekeeper/services/engine_factory.py` — 3-line shim dead
- `tests/test_pr237_review_fixes.py` → merged into `test_sweep_lock_hold.py` / `test_handlers.py`
- `tests/test_pr111_review_fixes.py` → merged into `test_metrics_store.py`
- `tests/test_lkpr78_critical_coverage.py` → split: MCP → `test_handlers.py`, Dashboard → `test_dashboard.py`
- `tests/test_lkpr58_link_candidate.py` → merged into `test_link_candidate.py` (create new)
- `tests/test_lkpr60_lkpr54.py` → merged into `test_memory_service.py` (create new)

### Create

- `src/lorekeeper/handlers.py` — extracted `_handle_*` functions from `server.py`
- `tests/test_link_candidate.py` — unified link candidate tests
- `tests/test_memory_service.py` — unified memory service tests

### Modify

- `src/lorekeeper/services/lancedb_engine.py` — strip `MemoryEngine` parent
- `src/lorekeeper/services/orchestrator.py` — `MemoryEngine` → `LanceDBEngine` type
- `src/lorekeeper/services/link_candidate.py` — `MemoryEngine` → `LanceDBEngine` in TYPE_CHECKING
- `src/lorekeeper/server.py` — use `LanceDBEngine` directly, import `_handle_*` from `handlers.py`
- `src/lorekeeper/serializers.py` — remove stale TYPE_CHECKING imports if orphaned
- `tests/test_handlers.py` — add MCP tests from LKPR-78
- `tests/test_dashboard.py` — add dashboard tests from LKPR-78
- `tests/test_metrics_store.py` — add PR111 regression tests

---

## Step-by-Step Implementation

### Step 1 — Remove MemoryEngine ABC + engine_factory

**1a. Edit `lancedb_engine.py`:**

- Remove `from lorekeeper.services.memory_engine import MemoryEngine`
- `class LanceDBEngine(MemoryEngine):` → `class LanceDBEngine:`
- Remove all `@abstractmethod` references (they're from the ABC, now dead)
- Seal the class (no abstract methods means no forced overrides needed)

**1b. Edit `orchestrator.py`:**

- `from lorekeeper.services.memory_engine import MemoryEngine` → `from lorekeeper.services.lancedb_engine import LanceDBEngine`
- `engine: MemoryEngine` → `engine: LanceDBEngine` in `__init__` signature

**1c. Edit `link_candidate.py`:**

- `from lorekeeper.services.memory_engine import MemoryEngine` (TYPE_CHECKING) → `from lorekeeper.services.lancedb_engine import LanceDBEngine`
- `engine: MemoryEngine` → `engine: LanceDBEngine` in `CosineScorer.__init__` and `LinkCandidateGenerator.__init__`

**1d. Edit `server.py`:**

- Remove `from lorekeeper.services.engine_factory import build_engine`
- Add `from lorekeeper.services.lancedb_engine import LanceDBEngine`
- `engine = build_engine(s.lancedb_path, s.embedding_model)` → `engine = LanceDBEngine(s.lancedb_path, s.embedding_model)`

**1e. Delete `services/memory_engine.py` and `services/engine_factory.py`**

**1f. Run tests:** `uv run pytest` — all pass

---

### Step 2 — Extract MCP handlers from server.py

**2a. Create `src/lorekeeper/handlers.py`:**

- Import all needed service/validation modules
- Move these functions from `server.py` (exact signature, exact body, no changes):

  - `_handle_search(svc, query, limit, ...)` — 80 lines
  - `_handle_insert(svc, memories, links, force)` — 20 lines
  - `_handle_recommend_links(svc, lore_id, top_k)` — 20 lines
  - `_VALID_SEARCH_FORMATS` constant
  - `_MAX_SUGGESTIONS_LIMIT` constant
  - `_VALID_REVIEW_ACTIONS` constant
  - `_handle_get_suggestions(svc, suggestions, limit, min_score)` — 20 lines
  - `_handle_review_suggestion(svc, suggestions, suggestion_ids, action)` — 140 lines

- Each `_handle_*` function receives `svc: MemoryService` and/or `suggestions: LinkSuggestionStore` as explicit params — no global state

**2b. Edit `server.py`:**

- Add: `from lorekeeper.handlers import _handle_search, _handle_insert, ...`
- Each MCP tool function calls the imported handler directly (already passes `get_service()`)
- Keep: module-level globals (`_svc`, `_suggestions_store`), `get_service()`, `get_suggestions_store()`, `init_service()`
- Keep: encouragement imports (`for_forget`, `for_insert`, etc.)
- Keep: all MCP tool decorators

**2c. Run tests:** `uv run pytest` — all pass

---

### Step 3 — Consolidate ticket-named test files

**3a. Create `tests/test_link_candidate.py`:**

- Copy content of `test_lkpr58_link_candidate.py` verbatim
- Remove `FakeVectorEngine` if `test_lkpr60_lkpr54.py` also has one (dedup if identical)

**3b. Create `tests/test_memory_service.py`:**

- Copy content of `test_lkpr60_lkpr54.py` verbatim

**3c. Edit `tests/test_handlers.py`:**

- Append MCP handler test classes from `test_lkpr78_critical_coverage.py`

**3d. Edit `tests/test_dashboard.py`:**

- Append dashboard API tests from `test_lkpr78_critical_coverage.py`

**3e. Edit `tests/test_metrics_store.py`:**

- Append regression tests from `test_pr111_review_fixes.py`

**3f. Edit `tests/test_sweep_lock_hold.py` (or `tests/test_handlers.py`):**

- Append sweep script regression test from `test_pr237_review_fixes.py`

**3g. Delete 5 original files:**

- `tests/test_pr237_review_fixes.py`
- `tests/test_pr111_review_fixes.py`
- `tests/test_lkpr78_critical_coverage.py`
- `tests/test_lkpr58_link_candidate.py`
- `tests/test_lkpr60_lkpr54.py`

**3h. Run tests:** `uv run pytest` — all pass

---

## Edge Cases and Decisions

| Case                                                         | Decision                                                                                                            |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `FakeVectorEngine` in both `test_lkpr58` and `test_lkpr60`   | Keep a single copy in `_helpers.py` or let each test file define its own (decouple tests from each other's helpers) |
| `test_handlers.py` already has a `TestHandlers` class        | Append new classes with distinct names — pytest discovers by class, not by file                                     |
| `test_dashboard.py` already has test classes                 | Append dashboard tests as new methods in existing classes or new classes                                            |
| test file rename breaks CI expectations                      | CI runs `uv run pytest` which discovers all test files in `tests/` — no file-name-based config to update            |
| Lines changed in `handlers.py` vs `server.py` are exact copy | No behavior change, no need to adjust test expectations                                                             |

## Test Plan Verification Mapping

| AC                                        | Verification                                          |
| ----------------------------------------- | ----------------------------------------------------- |
| ABC removed, LanceDBEngine is sole engine | `grep -r MemoryEngine src/` returns 0 hits            |
| engine_factory.py deleted                 | File no longer exists                                 |
| All type annotations updated              | `mypy src` passes                                     |
| handlers.py created, server.py slimmed    | `wc -l server.py` < 500                               |
| Test files consolidated                   | Each module has one test file, original files deleted |
| Full test suite green                     | `uv run pytest` exits 0                               |
| Ruff clean                                | `uv run ruff check src tests/` exits 0                |
| Mypy clean                                | `uv run mypy src` exits 0                             |

---

## Order of Execution

1. Step 1 — Remove ABC + factory (no deps)
2. `uv run pytest` — verify green
3. Step 2 — Extract handlers (no deps)
4. `uv run pytest` — verify green
5. Step 3 — Consolidate tests (depends on steps 1-2 being clean)
6. Full suite + lint + type-check
7. Self-review (score ≥ 8 gate)
