# LKPR-105 Phase 7 (v3): Delete `services/orchestrator.py` — Explicit DI + Processor Layer

**Type:** refactor
**Parent:** LKPR-104 (domain decomposition)
**Supersedes:** v1 (MemoryContext — rejected: god object by another name),
v2 (explicit DI but orchestration logic left inside presentation handlers).

**Delivery:** split into 12 small PRs (strangler pattern — facade lives until
Step 5). Per-step plans with exact files, verification commands, and
exception-list deltas: `docs/plans/lkpr-105/README.md`.

## Problem

LKPR-104 Phases 1-6 extracted business logic from the `MemoryService` god
object into focused domain services. Phase 5 left a temporary delegation facade
(`services/orchestrator.py`, 212 lines of pure delegation).

The facade creates architectural debt:

1. **Circular import**: every domain service imports `MemoryService` for
   `TYPE_CHECKING` — a reverse dependency from inner domains to the outer ring
2. **God-object coupling**: services reach through `svc._attr` for engine,
   stores, connection, cache, namespace filter
3. **Dead layer**: all callers could talk to domain services directly
4. **Test friction**: tests construct the full 9-arg facade even when they
   need one service

Additionally, use-case orchestration currently lives in the presentation
layer and is **duplicated across adapters**:

- `api/mcp/handlers/suggestion_handlers.py::handle_review_suggestion` and
  `dashboard/routes/suggestions.py::batch_suggestions` implement the same
  accept/reject batch loop twice — with silently divergent semantics
  (not-found → `skipped` in MCP vs `error` in dashboard; commit is
  conditional in MCP vs unconditional in dashboard)
- Metric increments and commit control are sprinkled across handlers, routes,
  and domain services

## Solution

Delete `services/orchestrator.py` and the `services/` package. **No
context/bundle object.** Two structural moves:

1. **Explicit constructor injection** — each domain service declares exactly
   the dependencies its methods use, as individual constructor parameters.
2. **New `processors/` layer** between presentation and domains — one
   processor per domain slice, owning use-case orchestration: input
   validation, metric increments, cross-service coordination, batch loops,
   and commit/transaction boundaries. Presentation adapters (MCP handlers,
   dashboard routes) become thin transport shims: parse transport input →
   call processor → serialize output.

`server.py` is the composition root that wires everything once.

## Dependency Direction — target graph (strictly one-directional)

### Horizontal layers (imports point DOWN only)

```
┌────────────────────────────────────────────────────────────┐
│  api/mcp, dashboard, cli/          (presentation adapters) │
│  server.py                         (composition root)      │
├────────────────────────────────────────────────────────────┤
│  shared/   (serializers, encouragement — presentation      │
│             helpers over domain models)                    │
├────────────────────────────────────────────────────────────┤
│  processors/  (use-case orchestration: validation,         │
│                metrics, batch loops, commit boundaries)    │
├────────────────────────────────────────────────────────────┤
│  domains/  (memory, link, reflection, suggestion —         │
│             single-aggregate business logic)               │
├────────────────────────────────────────────────────────────┤
│  platform/ (config, metrics — supporting repositories)     │
├────────────────────────────────────────────────────────────┤
│  infra/    (database, search_engine, keyword_index,        │
│             scheduler, logging, settings — zero business   │
│             vocabulary)                                    │
└────────────────────────────────────────────────────────────┘
```

Rules (each layer may import strictly below itself):

- `infra` imports **nothing** from lorekeeper except other `infra` modules
- `platform` imports only `infra`
- `domains` import `platform`, `infra`, other domains (per DAG below) — never
  `processors`, `shared`, `api`, `dashboard`, `server`
- `processors` import `domains`, `platform`, `infra` — never `shared`/`api`/
  `dashboard`/`server`. Processors return domain objects; they never serialize.
- `shared` imports `domains` and below (serializes domain models for
  presentation)
- `api`/`dashboard`/`cli` import `processors`, `shared`, and **domain
  `models` modules only** (for validation constants / type hints like
  `SOURCE_TYPES`, `RELATION_TYPES`). They must NOT import domain `service`/
  `repository` modules, `platform`, or `infra` (settings access goes through
  `server.get_settings()`).
- `server.py` (composition root) imports everything — it is the only module
  allowed to.

### Vertical domain slices (cross-domain DAG, acyclic)

```
suggestion ──→ memory ──→ link
reflection ──→ memory
```

`link` depends on no other domain. Processors mirror the slices 1:1
(`processors/memory.py`, `processors/link.py`, `processors/reflection.py`,
`processors/suggestion.py`, `processors/admin.py`) and may compose multiple
domain services — that is their job. Processors never import each other.

### Existing violations to fix (found by import audit of main)

All three are `infra` reaching UP; small, behavior-identical fixes:

| Violation                                                                                              | Fix                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `infra/database.py:31` imports `domains.link.models.RELATION_TYPES` for migration 4's CHECK constraint | Inline the frozen 12-string list. Also a correctness fix: migrations must be frozen snapshots — deriving one from the live constant means a future edit to `RELATION_TYPES` silently rewrites historical migration behavior. |
| `infra/keyword_index.py:3` imports `domains.memory.models.Memory`                                      | Local `typing.Protocol` (`id`, `title`, `description`, `content`). Call sites unchanged.                                                                                                                                     |
| `infra/scheduler.py:31` imports `platform.config.ConfigStore` (TYPE_CHECKING)                          | Local `typing.Protocol` (`get_overrides`, `set_override`).                                                                                                                                                                   |

### Enforcement — baked into the repo, hard to mess up

Three mechanisms, cheapest-feedback first:

1. **`tests/test_architecture.py`** (new, ~100 lines, stdlib `ast`, no new
   deps). Walks every module under `src/lorekeeper/`, extracts `lorekeeper.*`
   imports (including `if TYPE_CHECKING` blocks), asserts:
   - Layer rule per the table above (with the presentation exceptions:
     `shared`, `processors`, `domains.*.models` only)
   - Domain DAG rule: cross-domain edges limited to `suggestion→{memory,link}`,
     `reflection→{memory}`, `memory→{link}`
   - Processor isolation: no `processors.*` module imports another
     `processors.*` module; nothing below `processors` imports it
   - `services/` package does not exist
     The allowed-edges table lives IN the test as data — adding a new edge is a
     deliberate, reviewable one-line diff with a comment, not an accident.
2. **Pre-push hook** already runs unit tests → architecture test failures
   block push locally, not just in CI.
3. **`CLAUDE.md` + `docs/ARCHITECTURE.md`** get the layer diagram + the rule
   table, so agents (us) load the constraint into context before writing code.

## The Processor Layer

One module per domain slice under `src/lorekeeper/processors/`. Each processor
is a class taking its domain service(s) + `MetricsStore` + `Database` via
explicit constructor injection. Methods map 1:1 to use cases.

| Processor                                          | Constructor deps                                                       | Use-case methods (moved from)                                                                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `MemoryProcessor` (`processors/memory.py`)         | `search_service, write_service, import_service, metrics, db, settings` | `search()` + `search_by_ids()` (from `memory_handlers.handle_search` — enum/timestamp/ids-cap validation), `insert()` (from `handle_search`/`handle_insert`), `remember()`, `update()`, `forget()` (from `server.py` tool bodies), `import_dump()` (from backup route)                                                                                                                     |
| `LinkProcessor` (`processors/link.py`)             | `link_service, memories, links, metrics, db`                           | `create_link()`, `delete_link()`, `list_links()` (from `dashboard/routes/links.py` bodies)                                                                                                                                                                                                                                                                                                 |
| `ReflectionProcessor` (`processors/reflection.py`) | `reflection_service, metrics, db`                                      | `submit_reflection()`, `processed_session_ids()` (from `server.py` tool bodies)                                                                                                                                                                                                                                                                                                            |
| `SuggestionProcessor` (`processors/suggestion.py`) | `suggestion_service, suggestions_store, metrics, db`                   | `recommend_links()` (validation from `handle_recommend_links`), `get_pending()` (from `handle_get_suggestions`), `review()` — THE single batch accept/reject loop (unifies `handle_review_suggestion` + dashboard `batch_suggestions`; MCP semantics win: not-found → skipped, commit only when something changed — the dashboard route adapts its response shape from the unified result) |
| `AdminProcessor` (`processors/admin.py`)           | `config_store, metrics_store, suggestions_store, settings, db`         | `get_metrics()`, `get_config()/set_config()`, `trigger_sweep()`, `sweep_status()` (from dashboard metrics/config/suggestions routes — kills the `svc.config.set_override` + commit reach-through)                                                                                                                                                                                          |

Division of responsibility (goes verbatim into `docs/ARCHITECTURE.md`):

| Concern                                                                                                     | Layer                                                         |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Transport parsing, HTTP codes, MCP envelopes, response serialization                                        | presentation (`api/`, `dashboard/`, via `shared/serializers`) |
| Input validation, metric increments, multi-service coordination, batch loops, commit/transaction boundaries | `processors/`                                                 |
| Single-aggregate business rules (dedup, scoring, auto-link, cache)                                          | `domains/*/service.py`                                        |
| SQL / vector I/O                                                                                            | `domains/*/repository.py`, `platform/`, `infra/`              |

Consequences for domain services:

- **Metric increments move OUT of domain services** into processors
  (`MetricsStore.increment_metric_safe()`, the never-raise wrapper moved from
  the facade's `_increment_metric`). Domain services lose their `metrics`
  dependency entirely.
- **Commits move OUT of presentation** — routes/handlers never call
  `commit()`; processors own it via `db: Database` (`Database` gains
  `commit()`; `SuggestionService.accept_one`'s existing
  `svc.memories._db.transaction()` reach-in becomes an explicit `db` dep).
- Some processor methods are thin (one validation + one delegation). That is
  fine and expected — uniformity is what makes the layer enforceable. The
  rule "presentation imports processors only" has no exceptions to remember.

## Explicit DI — service signatures after

The facade's shared state gets three narrow homes (unchanged from v2):

1. **`MemoryCache`** (`domains/memory/cache.py`, new) — the LKPR-60 cache +
   BM25 rebuild (`all_memories()`, `invalidate()`, `rebuild_kw()`); deps:
   `memories, kw, ns_filter`. Single shared instance — real shared mutable
   state, but narrow: no services, no connection, no settings.
2. **`MetricsStore.increment_metric_safe()`** — documented exception to the
   no-inline-commit rule: metric writes are fire-and-forget best-effort;
   immediate commit + never-raise is the metric contract.
3. **`Database.commit()`** — processors take `db: Database` and own flush.

| Class                 | Constructor (pinned by grep of what method bodies use; final list verified at implementation)                                           |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `MemorySearchService` | `(engine, kw, memories, links, cache, settings, db, ns_filter)` — keeps `db`: usage-count bump on returned memories is a business write |
| `MemoryWriteService`  | `(engine, memories, links, cache, settings, db, namespace, ns_filter, link_service)`                                                    |
| `LinkService`         | `(links)`                                                                                                                               |
| `ReflectionService`   | `(reflections, db, cache, write_service)`                                                                                               |
| `SuggestionService`   | `(candidate_generator, engine, kw, memories, links, settings, db, ns_filter)`                                                           |
| `ImportService`       | `(engine, memories, links, cache, db, namespace)`                                                                                       |

(`metrics` is gone from every domain service — moved up to processors.)

`MemoryWriteService` is wide (9 params). Accepted: the width documents real
coupling instead of hiding it behind a bundle. If it hurts later, split the
service — don't re-bundle.

`extract_title` is already a free function; the `_extract_title` static shim
dies with the facade. Tests that monkey-patched `svc._extract_title` patch
`lorekeeper.domains.memory.service.extract_title` at module level.

Namespace values (`namespace`, `ns_filter`) are plain constructor parameters
computed once in `server.py`.

### Composition root — `server.py`

`init_service()` builds bottom-up: settings → engine → `Database` + migrate →
stores → config overrides → `KeywordIndex` → `ns_filter` → `MemoryCache` →
`LinkCandidateGenerator` → domain services (link → write → search →
reflection → suggestion → import) → **processors** → BM25 bootstrap via
`cache.rebuild_kw()` → sweep scheduler (unchanged, own DB connection).

Singleton getters exposed (each raises the standard "not initialised"
RuntimeError):

```
get_memory_processor()   get_link_processor()   get_reflection_processor()
get_suggestion_processor()   get_admin_processor()   get_settings()
```

`get_service()` and `get_suggestions_store()` are **deleted**. Presentation
code has exactly one kind of dependency: a processor (plus `get_settings()`
read-only). MCP tool bodies in `server.py` call processors directly.

## Files to Change

### Phase 7a — Core: cache, DI constructors, delete facade

| #   | File                                                 | Change                                                                              |
| --- | ---------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 1   | **NEW** `src/lorekeeper/domains/memory/cache.py`     | `MemoryCache` (moved from facade `_all_memories`/`_invalidate_cache`/`_rebuild_kw`) |
| 2   | `src/lorekeeper/infra/database.py`                   | Add `commit()` convenience                                                          |
| 3   | `src/lorekeeper/platform/metrics/repository.py`      | Add `increment_metric_safe()` (moved from facade `_increment_metric`)               |
| 4   | `src/lorekeeper/domains/memory/service.py`           | Explicit constructors per table; drop metrics; all `svc._x` → own attrs             |
| 5   | `src/lorekeeper/domains/link/service.py`             | `LinkService.__init__(links: LinkStore)`                                            |
| 6   | `src/lorekeeper/domains/reflection/service.py`       | Explicit constructor; `svc._extract_title` → free `extract_title`                   |
| 7   | `src/lorekeeper/domains/suggestion/service.py`       | Explicit constructor; `svc.memories._db.transaction()` → `self._db.transaction()`   |
| 8   | `src/lorekeeper/domains/memory/import_service.py`    | Explicit constructor                                                                |
| 9   | **DELETE** `src/lorekeeper/services/orchestrator.py` | —                                                                                   |
| 10  | **DELETE** `src/lorekeeper/services/__init__.py`     | `services/` package gone                                                            |

### Phase 7a′ — Layering fixes (infra imports nothing upward)

| #   | File                                    | Change                                                  |
| --- | --------------------------------------- | ------------------------------------------------------- |
| 11  | `src/lorekeeper/infra/database.py`      | Migration 4: inline frozen 12-string relation-type list |
| 12  | `src/lorekeeper/infra/keyword_index.py` | Local `Protocol` for indexable docs                     |
| 13  | `src/lorekeeper/infra/scheduler.py`     | Local `Protocol` for override store                     |

### Phase 7b — Processor layer

| #   | File                                              | Change                                                                                                    |
| --- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 14  | **NEW** `src/lorekeeper/processors/__init__.py`   | —                                                                                                         |
| 15  | **NEW** `src/lorekeeper/processors/memory.py`     | `MemoryProcessor` per table above                                                                         |
| 16  | **NEW** `src/lorekeeper/processors/link.py`       | `LinkProcessor`                                                                                           |
| 17  | **NEW** `src/lorekeeper/processors/reflection.py` | `ReflectionProcessor`                                                                                     |
| 18  | **NEW** `src/lorekeeper/processors/suggestion.py` | `SuggestionProcessor` incl. the single unified `review()` batch loop                                      |
| 19  | **NEW** `src/lorekeeper/processors/admin.py`      | `AdminProcessor`                                                                                          |
| 20  | `src/lorekeeper/server.py`                        | Composition root per above; delete `get_service()`/`get_suggestions_store()`; tool bodies call processors |

### Phase 7c — Presentation becomes thin shims

| #   | File                                      | Change                                                                                                     |
| --- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 21  | `api/mcp/handlers/memory_handlers.py`     | `handle_search(processor, ...)` — parse/serialize only; validation logic moved to `MemoryProcessor`        |
| 22  | `api/mcp/handlers/suggestion_handlers.py` | Batch loop DELETED — delegates to `SuggestionProcessor.review()`; serialize result                         |
| 23  | `dashboard/routes/search.py`              | `get_memory_processor().search(...)`                                                                       |
| 24  | `dashboard/routes/memories.py`            | `get_memory_processor()`                                                                                   |
| 25  | `dashboard/routes/backup.py`              | `get_memory_processor().import_dump(...)` + export via processor                                           |
| 26  | `dashboard/routes/links.py`               | `get_link_processor()`                                                                                     |
| 27  | `dashboard/routes/reflections.py`         | `get_reflection_processor()`                                                                               |
| 28  | `dashboard/routes/suggestions.py`         | Batch loop DELETED — `get_suggestion_processor().review()`; sweep trigger/status → `get_admin_processor()` |
| 29  | `dashboard/routes/metrics.py`             | `get_admin_processor().get_metrics(...)`                                                                   |
| 30  | `dashboard/routes/config.py`              | `get_admin_processor()` + `get_settings()`                                                                 |

### Phase 7d — Tests (relocation map below)

| #   | File                                                                                                                                                                                        | Change                                                                                                                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 31  | `tests/_helpers.py`                                                                                                                                                                         | Drop `build_service()`. Add `build_app(stores, engine, kw, settings) -> App` — tests-only dataclass bundle (domain services + processors + cache + db), wiring mirrors `server.init_service()` 1:1. Move `FakeEngine` here. |
| 32  | **NEW** `tests/test_architecture.py`                                                                                                                                                        | AST layer + DAG + processor-isolation enforcement                                                                                                                                                                           |
| 33  | **DELETE** `tests/test_orchestrator.py`                                                                                                                                                     | relocated per map                                                                                                                                                                                                           |
| 34  | **DELETE** `tests/test_memory_service.py`                                                                                                                                                   | relocated per map                                                                                                                                                                                                           |
| 35  | **NEW** `tests/domains/memory/test_write_service.py`                                                                                                                                        | see map                                                                                                                                                                                                                     |
| 36  | **NEW** `tests/domains/memory/test_search_service.py`                                                                                                                                       | see map                                                                                                                                                                                                                     |
| 37  | **NEW** `tests/domains/memory/test_cache.py`                                                                                                                                                | see map                                                                                                                                                                                                                     |
| 38  | **NEW** `tests/domains/link/test_service.py`                                                                                                                                                | see map                                                                                                                                                                                                                     |
| 39  | **NEW** `tests/domains/reflection/test_service.py`                                                                                                                                          | see map                                                                                                                                                                                                                     |
| 40  | **NEW** `tests/domains/suggestion/test_sweep.py`                                                                                                                                            | see map                                                                                                                                                                                                                     |
| 41  | `tests/test_handlers.py`                                                                                                                                                                    | Rewire to processors; absorb 2 handler-validation tests (map). Handler-level validation assertions now hit processor methods — same asserts, new entry point.                                                               |
| 42  | `tests/test_backend_coverage.py`, `tests/test_dashboard.py`, `tests/test_link_candidate.py`, `tests/test_metrics_store.py`, `tests/test_source_type_provenance.py`, `tests/e2e/conftest.py` | Setup/import updates only — test logic unchanged                                                                                                                                                                            |
| 43  | `tests/test_sweep_lock_hold.py`                                                                                                                                                             | Facade invariants → assert `lorekeeper.services` gone + sweep keeps own Database; update `init_service()` AST wiring check                                                                                                  |

### Phase 7e — Docs

| #   | File                   | Change                                                        |
| --- | ---------------------- | ------------------------------------------------------------- |
| 44  | `CLAUDE.md`            | Layer diagram + import rules + processor responsibility table |
| 45  | `docs/ARCHITECTURE.md` | Same, plus composition-root description; remove orchestrator  |

## Test Relocation Map

New test dirs mirror `src/lorekeeper/domains/`. Existing flat store/repo tests
stay put (moving them is out of scope).

### From `tests/test_orchestrator.py` (deleted, 1189 lines)

→ `tests/domains/memory/test_write_service.py` (32 tests):
test_insert_and_search, test_update_bumps_score,
test_soft_delete_on_low_confidence_not_useful,
test_insert_one_memory_missing_title_raises_clear_error,
test_extract_title_short_thought, test_extract_title_sentence_boundary,
test_extract_title_no_boundary_breaks_at_word,
test_new_memory_default_score_is_five, test_remember_stores_full_content,
test_remember_returns_none_linked_to_when_no_neighbor,
test_remember_auto_link_when_neighbor_above_threshold,
test_remember_no_auto_link_below_threshold,
test_remember_detects_duplicate_title, test_remember_auto_link_skips_self_match,
test_insert_with_inline_links, test_insert_inline_link_invalid_target,
test_insert_inline_link_invalid_relation,
test_insert_inline_links_invalid_format_string_not_list,
test_insert_inline_link_missing_target_memory_id,
test_insert_inline_link_missing_relation_type,
test_insert_auto_link_creates_link, test_insert_auto_link_respects_disabled,
test_insert_auto_link_respects_threshold, test_auto_link_duplicate_guard,
test_auto_link_uses_settings_k,
test_insert_with_inline_links_and_top_level_links,
test_insert_tags_with_agent_namespace,
test_insert_tags_with_shared_when_no_namespace,
test_same_title_different_namespace_not_duplicate,
test_same_title_same_namespace_still_detects_duplicate,
test_same_title_in_shared_still_detects_duplicate,
test_shared_agent_deduplicates_against_all_namespaces

→ `tests/domains/memory/test_search_service.py` (4 tests):
test_search_excludes_soft_deleted,
test_ids_sort_by_recent_malformed_updated_at_does_not_crash,
test_agent_reads_own_and_shared, test_no_namespace_sees_all

→ `tests/domains/link/test_service.py` (1 test):
test_insert_link_between_memories

→ `tests/domains/reflection/test_service.py` (13 tests):
test_submit_reflection_first_call_succeeds,
test_submit_reflection_duplicate_returns_noop,
test_submit_reflection_duplicate_does_not_create_extra_reflection_row,
test_reflect_auto_insert_creates_memories_from_discoveries,
test_reflect_auto_insert_creates_memories_from_lessons,
test_reflect_auto_insert_both_types, test_reflect_auto_insert_scores_correctly,
test_reflect_auto_insert_false_skips_creation,
test_reflect_auto_insert_empty_lists_returns_empty,
test_reflect_auto_insert_return_has_id_title_relation,
test_reflect_auto_insert_dedup_blocked_returns_existing_id,
test_reflect_auto_insert_memory_ids_populated,
test_reflect_auto_insert_partial_failure_continues

→ `tests/domains/suggestion/test_sweep.py` (class `TestSweepLinks`, 7 tests):
test_sweep_generates_suggestions, test_sweep_creates_no_real_links,
test_sweep_skips_already_linked, test_sweep_skips_rejected_pairs,
test_sweep_skips_pending_pairs, test_sweep_stats_structure,
test_sweep_prunes_expired

→ `tests/_helpers.py`: `FakeEngine`

### From `tests/test_memory_service.py` (deleted, 162 lines)

→ `tests/domains/memory/test_cache.py` (5 tests, target `MemoryCache`):
test_cache_initially_none, test_cache_populated_after_all_memories_call,
test_cache_invalidated_by_rebuild_kw, test_cache_returns_consistent_data,
test_include_deleted_false_filters_soft_deleted

→ `tests/domains/memory/test_write_service.py` (5 tests):
test_forget_soft_deletes_memory, test_forget_multiple_ids,
test_forget_unknown_id_goes_to_not_found, test_forget_invalidates_cache,
test_forgotten_memory_excluded_from_search

→ `tests/test_handlers.py` (2 tests — input-validation, now against
`MemoryProcessor.forget`): test_handle_forget_empty_ids_raises,
test_handle_forget_invalid_reason_raises

## What Stays the Same

- **Zero MCP behavior change** — every MCP tool produces identical output
- **One deliberate dashboard unification** (flagged, not silent):
  `/api/suggestions/batch` adopts the MCP review semantics (not-found →
  skipped instead of error; commit only when something changed). Response
  model shape (`BatchResponse`) unchanged. If Akane wants the old semantics
  preserved bit-for-bit, the processor takes a `strict_not_found` flag —
  decision surfaced in the PR description.
- No schema changes, no MCP API contract changes
- `suggestion/sweep.py`, `suggestion/candidate.py` untouched; `SweepService`
  keeps its own DB connection
- Relocated tests keep their logic verbatim — only imports + fixture setup
  change

## Risks

1. **`_extract_title` monkey-patch point** — patch
   `lorekeeper.domains.memory.service.extract_title` at module level.
2. **Processor layer adds one hop** for simple reads (metrics, reflections
   list). Accepted cost: the uniform "presentation → processors only" rule is
   what makes the architecture test simple and airtight — exceptions are what
   rot layering.
3. **Shared-instance discipline** — `MemoryCache` must be one instance shared
   by write/search/reflection/import services; `build_app()` mirrors
   production wiring 1:1 to prevent test/prod drift.
4. **Metric commit on shared connection** — `increment_metric_safe()` commits
   where the facade did; intentional, documented.
5. **Dashboard batch semantics unification** — see above; surfaced in PR.

## Acceptance Criteria

- [ ] `services/orchestrator.py` + `services/__init__.py` deleted — `src/lorekeeper/services/` gone
- [ ] **No context/bundle object in `src/`** — every domain service and processor takes explicit constructor deps; only new shared collaborator is `MemoryCache`
- [ ] **Processor layer exists and owns orchestration**: all metric increments, commit calls, and batch loops live in `processors/*`; zero `commit()`/`increment_metric` calls in `api/`, `dashboard/`, or `domains/*/service.py` (except `SuggestionService.accept_one`'s internal transaction)
- [ ] Suggestion review batch loop exists exactly once (`SuggestionProcessor.review`) — MCP handler and dashboard route both delegate to it
- [ ] **Dependency graph is one-directional**: `infra` → nothing; `platform` → `infra`; `domains` → `platform`/`infra` + DAG (`suggestion→{memory,link}`, `reflection→{memory}`, `memory→{link}`); `processors` → `domains` and below, no processor→processor; presentation → `processors` + `shared` + `domains.*.models` only; enforced by `tests/test_architecture.py`
- [ ] Three pre-existing infra→up violations fixed (`database.py`, `keyword_index.py`, `scheduler.py`)
- [ ] No module reaches into another object's privates (`._conn`, `._db`)
- [ ] `server.py` is the sole composition root; `get_service()`/`get_suggestions_store()` deleted; processor getters only
- [ ] Tests relocated exactly per the map; relocated test logic unchanged (imports/fixtures only)
- [ ] `uv run pytest -q --ignore=tests/e2e` green; `ruff check` zero new issues; `mypy src` clean
- [ ] `CLAUDE.md` + `docs/ARCHITECTURE.md` carry the layer diagram + rules table

## Diff Size Estimate

- Lines added: ~700 (5 processors ~400, cache, protocols, test_architecture, getters)
- Lines removed: ~550 (orchestrator, duplicated batch loop, handler validation bodies, old wiring)
- Test relocation: ~1350 lines moved (not rewritten)
- Files touched: ~45
