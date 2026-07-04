# LKPR-105 Phase 7 — Progress Tracker

**Goal:** Delete `services/orchestrator.py` (the `MemoryService` facade), introduce explicit constructor injection for all domain services, add a `processors/` layering enforcement via `tests/test_architecture.py`.

**Master plan:** `docs/plans/2026-07-03_134138-lkpr-105-phase7-delete-orchestrator.md`
**Step index:** `docs/plans/lkpr-105/README.md`

---

## Phase Map (Master Plan → Steps)

The master plan groups work into 6 phases (7a–7e). The README splits those into 12 small PRs (steps 0–7, with 3a/3b and 4a–4d). Each step is one session, one branch, one PR.

| Phase | Step | Branch                                             | Description                                                                | Depends on |
| ----- | ---- | -------------------------------------------------- | -------------------------------------------------------------------------- | ---------- | ------------------ |
| 7a′   | 0    | `chore/lkpr-105-step0-arch-test`                   | Architecture test with `TEMPORARY_ALLOWED` exception list                  | —          |
| 7a′   | 1    | `chore/lkpr-105-step1-infra-layering`              | Fix 3 infra→up violations (database, keyword_index, scheduler)             | 0          |
| 7a    | 2    | `chore/lkpr-105-step2-shared-collaborators`        | MemoryCache, Database.commit(), increment_metric_safe()                    | 0          |
| 7a    | 3a   | `chore/lkpr-105-step3a-di-narrow`                  | Explicit DI for LinkService, ImportService, ReflectionService              | 2          | :white_check_mark: |
| 7a    | 3b   | `chore/lkpr-105-step3a-di-narrow`                  | Explicit DI for MemorySearchService, MemoryWriteService, SuggestionService | 3a         | :white_check_mark: |
| 7b    | 4a   | `chore/lkpr-105-step4a-suggestion-processor`       | SuggestionProcessor (kill duplicated batch loop)                           | 2          |
| 7b    | 4b   | `chore/lkpr-105-step4b-memory-processor`           | MemoryProcessor (search/insert/remember/update/forget/import)              | 3b         |
| 7b    | 4c   | `chore/lkpr-105-step4c-reflection-link-processors` | ReflectionProcessor + LinkProcessor                                        | 3b         |
| 7b    | 4d   | `chore/lkpr-105-step4d-admin-processor`            | AdminProcessor (metrics/config/sweep)                                      | 2          |
| 7c    | 5    | `chore/lkpr-105-step5-delete-facade`               | Delete services/ — server.py is the composition root                       | 4a–4d      |
| 7d    | 6    | `chore/lkpr-105-step6-test-relocation`             | Move tests to domain-mirroring directories                                 | 5          |
| 7e    | 7    | `chore/lkpr-105-step7-docs`                        | Update CLAUDE.md + ARCHITECTURE.md                                         | 5          |

---

## Current State

**Status:** Steps 0-3b done (on same branch, Phase 3 complete)

**Current branch:** `chore/lkpr-105-step3a-di-narrow` (also contains Step 3b)
**Working tree:** clean (branch ready for PR)

---

## Dependency Graph

```
Step 0 ──┬── Step 1 ──┬──────────────────────────────────────────────── Step 5 ──┬── Step 6
         │            │                                                         │
         └── Step 2 ──┼── Step 3a ── Step 3b ──┬── Step 4b ──────────────────────┤
                      │                         │                               │
                      │                         └── Step 4c ─────────────────────┘
                      │                                                         │
                      ├── Step 4a (needs only Step 2) ──────────────────────────┘
                      │                                                         │
                      └── Step 4d (needs only Step 2) ──────────────────────────┘
                                                                                │
                                                                                └── Step 7
```

Key parallelization opportunities:

- Steps 1, 2, 4a, 4d can all start after Step 0
- Steps 4a and 4d need only Step 2 (not 3a/3b)
- Steps 6 and 7 can run in parallel after Step 5

---

## Exception Entries (TEMPORARY_ALLOWED)

The `tests/test_architecture.py` test has a `TEMPORARY_ALLOWED` set. Each step must delete its entries. The set must be empty after Step 5.

Entry format: `(importer_module, imported_module)` — `# Step N removes`

| Step removes | Entry                                                                                 | Status  |
| ------------ | ------------------------------------------------------------------------------------- | ------- |
| 1            | `(lorekeeper.infra.database, lorekeeper.domains.link.models)`                         | NOT YET |
| 1            | `(lorekeeper.infra.keyword_index, lorekeeper.domains.memory.models)`                  | NOT YET |
| 1            | `(lorekeeper.infra.scheduler, lorekeeper.platform.config.repository)`                 | NOT YET |
| 3a           | `(lorekeeper.domains.link.service, lorekeeper.services.orchestrator)`                 | DONE    |
| 3a           | `(lorekeeper.domains.memory.import_service, lorekeeper.services.orchestrator)`        | DONE    |
| 3a           | `(lorekeeper.domains.reflection.service, lorekeeper.services.orchestrator)`           | DONE    |
| 3b           | `(lorekeeper.domains.memory.service, lorekeeper.services.orchestrator)`               | DONE    |
| 3b           | `(lorekeeper.domains.suggestion.service, lorekeeper.services.orchestrator)`           | DONE    |
| 4a/4b/4c     | `(lorekeeper.api.mcp.handlers.memory_handlers, lorekeeper.services.orchestrator)`     | NOT YET |
| 4b           | `(lorekeeper.api.mcp.handlers.memory_handlers, lorekeeper.domains.memory.ranking)`    | NOT YET |
| 4a           | `(lorekeeper.api.mcp.handlers.suggestion_handlers, lorekeeper.services.orchestrator)` | NOT YET |
| 5            | `(lorekeeper.server, lorekeeper.services.orchestrator)`                               | NOT YET |

**Note:** The seed entries above are the _expected_ set based on the plan. The actual `TEMPORARY_ALLOWED` set must be generated by running the collector on the current `main` — the seed must exactly match the audit output. Implementation in Step 0 will produce the definitive list.

---

## Step-by-Step Session Handoff

### How to use this doc

Each new session starts here. Read the current state, then pick the next unstarted step that has all its dependencies satisfied. Each step below has the exact info needed to execute it.

### Step 0 — Architecture test with TEMPORARY_ALLOWED

**Branch:** `chore/lkpr-105-step0-arch-test`
**Depends on:** nothing
**Files:** 1 new (`tests/test_architecture.py`)
**Size:** ~110 lines

**Plan:** `docs/plans/lkpr-105/step-0-architecture-test.md`

**Key actions:**

1. Create `tests/test_architecture.py` — pure stdlib `ast` walker, layer classification, 6 rules
2. Seed `TEMPORARY_ALLOWED` from collector output (run on `main`, paste verbatim)
3. Add stale-entry guard test
4. Verify: `uv run pytest tests/test_architecture.py -v` passes
5. Verify: `uv run pytest -q --ignore=tests/e2e` green
6. Verify: `uv run ruff check src tests scripts/ && uv run mypy src`
7. Negative check: temporarily add a violation, test must catch it, revert
8. Open PR

**Branch base:** `main` (first step)

**Verification:**

```bash
uv run pytest tests/test_architecture.py -v
uv run pytest -q --ignore=tests/e2e
uv run ruff check src tests scripts/ && uv run mypy src
```

---

### Step 1 — Infra layering fixes

**Branch:** `chore/lkpr-105-step1-infra-layering`
**Depends on:** Step 0 merged
**Files:** 3 modified + test_architecture (delete 3 entries)
**Size:** ~40 lines

**Plan:** `docs/plans/lkpr-105/step-1-infra-layering.md`

**Key actions:**

1. `infra/database.py`: inline frozen 12-string relation-type list in migration 4 (derive from `main` first, add regression test)
2. `infra/keyword_index.py`: replace `Memory` import with local `Protocol`
3. `infra/scheduler.py`: replace `ConfigStore` TYPE_CHECKING import with local `Protocol`
4. Delete 3 Step 1 exception entries from `tests/test_architecture.py`
5. Verify: `grep -rn "from lorekeeper" src/lorekeeper/infra/ --include='*.py' | grep -v "lorekeeper.infra"` → empty

**Branch base:** `main` (independent of Step 0, but Step 0 must exist first to have the test file to edit)

---

### Step 2 — Shared collaborators

**Branch:** `chore/lkpr-105-step2-shared-collaborators`
**Depends on:** Step 0
**Files:** 1 new, 3 modified, 1 new test file
**Size:** ~180 lines

**Plan:** `docs/plans/lkpr-105/step-2-shared-collaborators.md`

**Key actions:**

1. NEW `src/lorekeeper/domains/memory/cache.py` — `MemoryCache` (move 3 facade methods)
2. `infra/database.py` — add `commit()` method
3. `platform/metrics/repository.py` — add `increment_metric_safe()` (move from facade)
4. `services/orchestrator.py` — delegate to new collaborators
5. NEW `tests/domains/memory/test_cache.py` — direct MemoryCache tests
6. Verify: no caller changes, no new architecture exceptions

---

### Step 3a — Explicit DI: narrow services

**Branch:** `chore/lkpr-105-step3a-di-narrow`
**Depends on:** Step 2
**Files:** 3 service files + orchestrator + test_architecture (delete 3 entries)
**Size:** ~150 lines

**Plan:** `docs/plans/lkpr-105/step-3a-explicit-di-narrow.md`

**Key actions:**

1. `domains/link/service.py`: `__init__(self, links: LinkStore)` — drop `MemoryService`
2. `domains/memory/import_service.py`: `__init__(self, engine, memories, links, cache, db, namespace)`
3. `domains/reflection/service.py`: `__init__(self, reflections, metrics, db, cache, write_service)` — `svc._extract_title` → `extract_title` free function
4. `services/orchestrator.py`: update construction order, thread `db: Database` param
5. `tests/test_sweep_lock_hold.py`: update invariant (sweep still gets own DB)
6. Delete 3 domain→orchestrator exception entries
7. Verify: `grep -n "MemoryService" src/lorekeeper/domains/link/service.py ...` → empty

**Pitfalls:**

- `test_sweep_lock_hold` asserts no `db` param on facade — update with rationale
- `_extract_title` monkey-patch: any tests patching `svc._extract_title` must now patch `lorekeeper.domains.memory.service.extract_title`

---

### Step 3b — Explicit DI: wide services

**Branch:** `chore/lkpr-105-step3b-di-wide`
**Depends on:** Step 3a
**Files:** 2 service files + orchestrator + test_architecture (delete 2 entries)
**Size:** ~200 lines

**Plan:** `docs/plans/lkpr-105/step-3b-explicit-di-wide.md`

**Key actions:**

1. `domains/memory/service.py`: split into `MemorySearchService` and `MemoryWriteService` with explicit constructors
2. `domains/suggestion/service.py`: explicit constructor, kill `svc.memories._db` reach-in via `self._db`
3. `services/orchestrator.py`: full construction order, `LinkCandidateGenerator` stays in facade init
4. Delete 2 remaining domain→orchestrator entries
5. After this step: `grep -rn "MemoryService\|services.orchestrator" src/lorekeeper/domains/` → empty

**Pitfalls:**

- `MemoryWriteService` is wide (9-10 params) — intentional, no bundle
- `svc.memories._db.transaction()` → `self._db.transaction()` — kills last private reach-in
- Monkey-patch migration for `_extract_title` / `_all_memories` if any tests target them

---

### Step 4a — SuggestionProcessor

**Branch:** `chore/lkpr-105-step4a-suggestion-processor`
**Depends on:** Step 2 only (can run before/parallel to Step 3)
**Files:** 2 new, 3 modified, exception entries deleted
**Size:** ~220 lines

**Plan:** `docs/plans/lkpr-105/step-4a-suggestion-processor.md`

**Key actions:**

1. NEW `src/lorekeeper/processors/__init__.py` (empty)
2. NEW `src/lorekeeper/processors/suggestion.py` — `SuggestionProcessor` with `recommend_links()`, `get_pending()`, `review()`
3. `api/mcp/handlers/suggestion_handlers.py` — gut to shims
4. `dashboard/routes/suggestions.py` — `batch_suggestions` delegates to processor
5. `server.py` — construct + getter + rewire tool bodies
6. NEW `tests/processors/test_suggestion_processor.py`
7. Delete exception entries

**Pitfalls:**

- Until Step 3b lands, processor reaches services via facade (`svc.suggestion_service`) — processor constructor signature is final; only wiring changes later
- Dashboard batch semantics unify: not-found → `skipped` (MCP wins). Flag in PR description
- `get_suggestions_store()` stays for now (dies in 4d/5)

---

### Step 4b — MemoryProcessor

**Branch:** `chore/lkpr-105-step4b-memory-processor`
**Depends on:** Step 3b
**Files:** 1 new, 5 modified
**Size:** ~260 lines

**Plan:** `docs/plans/lkpr-105/step-4b-memory-processor.md`

**Key actions:**

1. NEW `src/lorekeeper/processors/memory.py` — `MemoryProcessor(search_service, write_service, import_service, metrics, db, settings)`
2. `api/mcp/handlers/memory_handlers.py` — thin shim, serialize only
3. `server.py` — construct + getter + rewire tool bodies
4. `dashboard/routes/search.py`, `backup.py`, `memories.py` — delegate to processor
5. NEW `tests/processors/test_memory_processor.py` — validation tests
6. Metric increments move OUT of domain services, INTO processor
7. Verify: `grep -rn "increment_metric" src/lorekeeper/domains/memory/` → empty

---

### Step 4c — ReflectionProcessor + LinkProcessor

**Branch:** `chore/lkpr-105-step4c-reflection-link-processors`
**Depends on:** Step 3b
**Files:** 2 new, 4 modified
**Size:** ~150 lines

**Plan:** `docs/plans/lkpr-105/step-4c-reflection-link-processors.md`

**Key actions:**

1. NEW `src/lorekeeper/processors/reflection.py` — `ReflectionProcessor(reflection_service, metrics, db)`
2. NEW `src/lorekeeper/processors/link.py` — `LinkProcessor(link_service, memories, links, metrics, db)`
3. `server.py` — construct + getters + rewire
4. `dashboard/routes/reflections.py`, `links.py` — delegate writes
5. NEW processor tests
6. Verify: `grep -n "commit()" src/lorekeeper/dashboard/routes/links.py src/lorekeeper/dashboard/routes/reflections.py` → empty

---

### Step 4d — AdminProcessor

**Branch:** `chore/lkpr-105-step4d-admin-processor`
**Depends on:** Step 2 (not Step 3)
**Files:** 1 new, 4 modified
**Size:** ~150 lines

**Plan:** `docs/plans/lkpr-105/step-4d-admin-processor.md`

**Key actions:**

1. NEW `src/lorekeeper/processors/admin.py` — `AdminProcessor(config, metrics, suggestions, settings, db)`
2. `dashboard/routes/metrics.py`, `config.py`, `suggestions.py` — delegate
3. `server.py` — construct + getter
4. Delete `get_suggestions_store()` if last caller gone
5. NEW `tests/processors/test_admin_processor.py`
6. Verify: `grep -rn "get_service\|get_suggestions_store" src/lorekeeper/dashboard/routes/` → empty
7. Verify: `grep -rn "commit()" src/lorekeeper/dashboard/ src/lorekeeper/api/` → empty

---

### Step 5 — Delete the facade

**Branch:** `chore/lkpr-105-step5-delete-facade`
**Depends on:** 4a, 4b, 4c, 4d all merged
**Files:** 2 deleted, ~4 modified — mostly deletions
**Size:** net −300 lines

**Plan:** `docs/plans/lkpr-105/step-5-delete-facade.md`

**Key actions:**

1. DELETE `src/lorekeeper/services/orchestrator.py` + `services/__init__.py`
2. `server.py` — full composition root, delete `get_service()`/`get_suggestions_store()`, processor getters only
3. `tests/_helpers.py` — delete `build_service()`, add `build_app()` + `App` dataclass
4. `tests/test_sweep_lock_hold.py` — replace facade-invariant checks with `services`-gone check
5. Delete remaining exception entries → `TEMPORARY_ALLOWED` now empty
6. Delete the `TEMPORARY_ALLOWED` set and exception mechanism
7. E2E run locally

**Precondition check:**

```bash
grep -rn "get_service\|MemoryService" src/lorekeeper/ --include='*.py' | grep -v services/
# Expected: only server.py
```

**Verification:**

```bash
test ! -d src/lorekeeper/services && echo GONE
grep -rn "MemoryService" src/ tests/ --include='*.py'  # → empty
uv run python -c "from lorekeeper.server import init_service"  # imports clean
```

---

### Step 6 — Test relocation

**Branch:** `chore/lkpr-105-step6-test-relocation`
**Depends on:** Step 5
**Files:** 2 deleted, 6 created, moves only
**Size:** moves only (~1350 lines relocated)

**Plan:** `docs/plans/lkpr-105/step-6-test-relocation.md`

**Key actions:**

1. DELETE `tests/test_orchestrator.py` → distribute to:
   - `tests/domains/memory/test_write_service.py` (32 tests)
   - `tests/domains/memory/test_search_service.py` (4 tests)
   - `tests/domains/link/test_service.py` (1 test)
   - `tests/domains/reflection/test_service.py` (13 tests)
   - `tests/domains/suggestion/test_sweep.py` (7 tests)
   - `tests/_helpers.py`: `FakeEngine`
2. DELETE `tests/test_memory_service.py` → distribute to:
   - 5 cache tests: DELETE (Step 2 created direct tests)
   - 5 forget tests → `tests/domains/memory/test_write_service.py`
   - 2 validation tests → `tests/processors/test_memory_processor.py`
3. Use `git mv`-style — bodies verbatim, only imports/fixtures change

**Verification:**

```bash
# Count invariance:
git stash && uv run pytest --collect-only -q --ignore=tests/e2e | tail -1 && git stash pop
uv run pytest --collect-only -q --ignore=tests/e2e | tail -1
# totals must match, minus 5 deliberately-deleted duplicate cache tests
```

---

### Step 7 — Docs

**Branch:** `chore/lkpr-105-step7-docs`
**Depends on:** Step 5 (can run parallel to Step 6)
**Files:** 2 modified, docs only

**Plan:** `docs/plans/lkpr-105/step-7-docs.md`
**Source material:** `docs/plans/lkpr-105/step-7-architecture-reference.md`

**Key actions:**

1. `CLAUDE.md` — replace section with layer diagram, import rules, responsibility table
2. `docs/ARCHITECTURE.md` — replace entire file with architecture reference
3. Remove all stale `MemoryService`/`orchestrator` references
4. Build order list updated

**Verification:**

```bash
uv run mkdocs build --strict
grep -rn "orchestrator\|MemoryService" CLAUDE.md docs/ARCHITECTURE.md  # → empty (except historical)
```

---

## Running Notes

_Record decisions, gotchas, and unexpected findings here as the refactor progresses._

| Date | Step       | Note |
| ---- | ---------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|      | 2026-07-04 | 0-1  | Combined PR #268 — Steps 0 (architecture test) + 1 (infra layering fixes) in one PR. 36 TEMPORARY_ALLOWED entries remain. Plan files (docs/plans/lkpr-105/) included in PR.                                                                                                      |
|      | 2026-07-04 | 2    | PR #269 — MemoryCache, Database.commit(), increment_metric_safe() extracted from facade. 6 direct cache tests. No new architecture exceptions.                                                                                                                                   |
|      | 2026-07-04 | 3a   | Branch `chore/lkpr-105-step3a-di-narrow` — Step 3a complete. Explicit DI for LinkService, ImportService, ReflectionService. 3 domain→orchestrator exception entries deleted. `db: Database` threaded into MemoryService. Sweep isolation invariant updated.                      |
|      | 2026-07-04 | 3b   | Same branch — Step 3b complete. Explicit DI for MemorySearchService, MemoryWriteService, SuggestionService. `row_to_memory` moved to `models.py` (circular import fix). All 5 domain→orchestrator entries deleted. Zero `MemoryService` imports in `domains/`. Phase 3 complete. |

---

## Session Handoff Protocol

Each session ends with:

1. **Open PR** for the step (if not already done)
2. **Update this doc** — mark the step as done, update Running Notes
3. **Save to Lorekeeper** — `mcp_lorekeeper_lore_reflect` with session summary
4. **Update `TEMPORARY_ALLOWED`** entries in `tests/test_architecture.py` (next session verifies)
5. **State the next step** to start — branch name, depends-on, plan file

**Next session start sequence:**

1. `git status` — verify clean working tree
2. `git branch --show-current` — verify correct branch
3. Read this doc — find the next unstarted step with all deps met
4. Load the step's plan file from `docs/plans/lkpr-105/step-*.md`
5. `git checkout -b <step-branch> main` or `git checkout <step-branch>` if branch exists
