# LKPR-104: Clean Architecture Reorg — Plan

**Ticket:** `backlogs/ready/LKPR-104-clean-architecture-reorg.md` · **Issue:** #255
**Author:** Diana · **Date:** 2026-07-01
**Type:** structural refactor, zero behavior change, zero MCP API surface change

## Goals

1. **Horizontal layering** (Clean Architecture rings): API -> Service -> Reusable
   module -> Repository -> Infra, dependencies point inward only.
2. **Vertical slicing** (DDD): one directory per core entity — `memory`, `link`,
   `suggestion`, `reflection` — each owning its own models, repository, service,
   and reusable logic.
3. Fix two concrete boundary violations found during the codebase-health audit
   (dashboard reaching into `svc._conn`; `ConfigStore` committing inline).
4. Retire the `MemoryService` god object (1046 lines, 9+ responsibilities).

## Non-goals

- No data migration. `~/.lorekeeper` on-disk format is untouched.
- No MCP tool name/schema changes — hard constraint from CLAUDE.md, verified
  at every phase gate.
- No new abstract interfaces except one justified `UnitOfWork`/`transaction()`
  (fixes a real bug, not speculative DIP).
- No behavior/logic changes bundled with mechanical moves — logic changes
  (Phase 5, Phase 6b) are isolated in their own PRs.

## Ring definitions

| Ring            | Directory                                             | Knows business vocabulary?                      | May import from                                                                                       |
| --------------- | ----------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| API             | `api/`                                                | No — only DTOs in/out                           | domain `service.py` only                                                                              |
| Service         | `domains/*/service.py`                                | Yes — use-case orchestration, owns transactions | own domain's reusable modules + repository; other domains' `service.py` (never their `repository.py`) |
| Reusable module | `domains/*/{ranking,dedup,feedback,candidate}.py`     | Yes — pure functions, zero I/O                  | nothing (stdlib/3rd-party only)                                                                       |
| Repository      | `domains/*/repository.py`, `platform/*/repository.py` | Lightly — typed rows                            | `infra/database.py` only                                                                              |
| Infra           | `infra/`                                              | No                                              | nothing internal                                                                                      |

**Enforcement:** each phase's PR review checks import direction manually (no
import-linter tooling added — not worth the dependency for a single-maintainer
repo; revisit if the rule gets violated twice).

## Target tree (end state, post Phase 7)

```
src/lorekeeper/
├── domains/
│   ├── memory/
│   │   ├── models.py          # Memory, SourceType, SOURCE_TYPES, WRITE_SOURCE_TYPES
│   │   ├── repository.py      # was services/memory_store.py
│   │   ├── ranking.py         # was services/search.py (rank_results, parse_iso_utc, SearchResult)
│   │   ├── dedup.py           # was services/dedup.py
│   │   ├── feedback.py        # was services/feedback.py
│   │   ├── import_service.py  # was orchestrator.import_dump()
│   │   └── service.py         # MemorySearchService + MemoryWriteService
│   ├── link/
│   │   ├── models.py          # MemoryLink, RelationType, RELATION_TYPES, TYPE_MIGRATION_MAP
│   │   ├── repository.py      # was services/link_store.py
│   │   └── service.py         # was orchestrator._insert_one_link/_validate_relation_type
│   ├── suggestion/
│   │   ├── models.py          # LinkSuggestion
│   │   ├── repository.py      # was services/suggestion_store.py
│   │   ├── candidate.py       # was services/link_candidate.py
│   │   ├── sweep.py           # was services/sweep_service.py
│   │   └── service.py         # accept_batch()/reject_batch() — owns transaction boundary
│   └── reflection/
│       ├── models.py          # Reflection, SessionRecord
│       ├── repository.py      # was services/reflection_store.py
│       └── service.py         # was orchestrator.submit_reflection/get_processed_session_ids
├── platform/
│   ├── config/repository.py   # was services/config_store.py, inline commit() removed
│   └── metrics/repository.py  # was services/metrics_store.py
├── infra/
│   ├── database.py            # was services/database.py + new Database.transaction()
│   ├── search_engine.py       # was services/lancedb_engine.py
│   ├── keyword_index.py       # was services/keyword_index.py
│   ├── scheduler.py           # unchanged location semantics, moved into infra/
│   ├── logging_setup.py       # moved into infra/
│   └── settings.py            # was config.py
├── shared/
│   ├── serializers.py         # unchanged content, moved
│   └── encouragement.py       # unchanged content, moved
├── api/
│   ├── mcp/
│   │   ├── server.py          # tool decorators + composition root (init_service)
│   │   └── handlers/
│   │       ├── memory_handlers.py
│   │       ├── reflection_handlers.py
│   │       └── suggestion_handlers.py
│   └── dashboard/              # existing dashboard/ tree, routes updated to call domain services
├── cli/                         # unchanged
└── __main__.py                  # unchanged
```

## Phase-by-phase execution plan

Each phase: **branch from `origin/main`** -> move/split files -> update imports
-> `uv run pytest` green -> `uv run ruff check src tests scripts/` clean ->
`uv run mypy src` clean -> diff MCP tool schema against Phase 0 baseline ->
self-review gate (score >= 8) -> PR -> merge -> next phase branches from the
new `main`.

### Phase 0 — Baseline (no code change)

- Run full suite, record pass/fail count and timing.
- Run `ruff check src tests scripts/`, `uv run mypy src` — record clean state.
- Snapshot MCP tool schemas: dump `mcp.tool` registrations (names + input
  schemas) from `server.py` to `docs/plans/lkpr-104-mcp-baseline.json`. This
  is the diff target for every later phase's "no API surface change" check.
- No PR — this is a recorded checkpoint, committed as a docs-only change if
  the baseline file is kept, or just noted in the phase tracking below if not.

### Phase 1 — `infra/` ring

**Move (no logic change):**

| From                         | To                       |
| ---------------------------- | ------------------------ |
| `services/database.py`       | `infra/database.py`      |
| `services/lancedb_engine.py` | `infra/search_engine.py` |
| `services/keyword_index.py`  | `infra/keyword_index.py` |
| `scheduler.py`               | `infra/scheduler.py`     |
| `logging_setup.py`           | `infra/logging_setup.py` |
| `config.py`                  | `infra/settings.py`      |

Update every `from lorekeeper.services.database import Database` etc. across
`src/` and `tests/`. Class/function names unchanged — only module paths move.

### Phase 2 — `platform/` ring

| From                        | To                               |
| --------------------------- | -------------------------------- |
| `services/config_store.py`  | `platform/config/repository.py`  |
| `services/metrics_store.py` | `platform/metrics/repository.py` |

Pure move. The inline-`commit()` bug fix in `ConfigStore` is deliberately
**deferred to Phase 6b** — do not fix logic bugs inside a mechanical-move
phase.

### Phase 3 — `domains/*/repository.py` + `domains/*/models.py`

Split `models.py` into four files by entity:

| Model(s)                                                             | New file                       |
| -------------------------------------------------------------------- | ------------------------------ |
| `Memory`, `SourceType`, `SOURCE_TYPES`, `WRITE_SOURCE_TYPES`         | `domains/memory/models.py`     |
| `MemoryLink`, `RelationType`, `RELATION_TYPES`, `TYPE_MIGRATION_MAP` | `domains/link/models.py`       |
| `LinkSuggestion`                                                     | `domains/suggestion/models.py` |
| `Reflection`, `SessionRecord`                                        | `domains/reflection/models.py` |

Move repositories:

| From                           | To                                 |
| ------------------------------ | ---------------------------------- |
| `services/memory_store.py`     | `domains/memory/repository.py`     |
| `services/link_store.py`       | `domains/link/repository.py`       |
| `services/suggestion_store.py` | `domains/suggestion/repository.py` |
| `services/reflection_store.py` | `domains/reflection/repository.py` |

`types.yaml` stays at package root (loaded by `domains/link/models.py` via
the same relative-path pattern `models.py` used).

### Phase 4 — Reusable modules + shared/

| From                         | To                                |
| ---------------------------- | --------------------------------- |
| `services/search.py`         | `domains/memory/ranking.py`       |
| `services/dedup.py`          | `domains/memory/dedup.py`         |
| `services/feedback.py`       | `domains/memory/feedback.py`      |
| `services/link_candidate.py` | `domains/suggestion/candidate.py` |
| `services/sweep_service.py`  | `domains/suggestion/sweep.py`     |
| `serializers.py`             | `shared/serializers.py`           |
| `services/encouragement.py`  | `shared/encouragement.py`         |

Verify at this phase: none of these modules import anything from `api/` or
any `repository.py` — they must stay pure/stateless. `sweep.py` takes
repository instances via constructor injection already (confirmed in original
`sweep_service.py` — no change needed there beyond the import path).

### Phase 5 — Split the orchestrator (highest-risk phase)

This is the only phase with real logic extraction — treat it as N
independent, testable extractions, not one big rewrite:

1. Add `Database.transaction()` context manager to `infra/database.py` —
   wraps `BEGIN`/`COMMIT`/`ROLLBACK` (or `SAVEPOINT` for nested use, matching
   the existing pattern in `dashboard/routes/suggestions.py`). Unit test it
   in isolation first.
2. Create `domains/memory/service.py` — move `search`, `search_by_ids`,
   `insert`, `remember`, `_remember_with_score`, `_auto_link`,
   `_insert_one_memory`, `update`, `forget`, `_all_memories`,
   `_invalidate_cache`, `_rebuild_kw`, `_extract_title`. Constructor takes
   `MemoryRepository`, `LinkRepository` (for auto-link target checks),
   `SearchEngine`, `KeywordIndex`, `Settings`.
3. Create `domains/memory/import_service.py` — move `import_dump` (125 lines)
   out on its own; it's a rare admin path, not part of the hot-path class.
4. Create `domains/link/service.py` — move `_insert_one_link`,
   `_validate_relation_type`.
5. Create `domains/suggestion/service.py` — move `recommend_links`; add
   `accept_batch()`/`reject_batch()` as NEW methods that internally use
   `Database.transaction()` (these don't exist yet on the orchestrator —
   the equivalent logic currently lives inline in
   `dashboard/routes/suggestions.py:batch_suggestions`, but extraction only,
   no dashboard route change yet — that's Phase 6b).
6. Create `domains/reflection/service.py` — move `submit_reflection`,
   `get_processed_session_ids`. This service calls
   `domains/memory/service.py`'s `MemoryWriteService.remember()` for
   auto-insert — cross-domain call goes service-to-service, never
   service-to-repository.
7. Keep a **temporary facade**: `services/orchestrator.py` shrinks to a thin
   `MemoryService` class whose methods delegate 1:1 to the five new services,
   preserving every existing public method name/signature
   (`svc.search(...)`, `svc.insert(...)`, `svc.commit()`, `svc.memories`,
   `svc.links`, etc.) so `handlers.py` and dashboard routes need zero changes
   in this phase. This facade is deleted in Phase 7.
8. Move every test in `test_orchestrator.py`/`test_memory_service.py` to the
   matching new `test_<domain>_service.py` file — one-to-one method mapping,
   no test logic changes.

**Self-review gate applies hardest here** — after extraction, diff the moved
method bodies against the original line-by-line to confirm zero logic drift
before opening the PR.

### Phase 6a — Split handlers (mechanical)

| From (function in `handlers.py`)                                               | To                                        |
| ------------------------------------------------------------------------------ | ----------------------------------------- |
| `handle_search`, `handle_insert`                                               | `api/mcp/handlers/memory_handlers.py`     |
| (reflect handler — currently inline in `server.py`, extract it)                | `api/mcp/handlers/reflection_handlers.py` |
| `handle_recommend_links`, `handle_get_suggestions`, `handle_review_suggestion` | `api/mcp/handlers/suggestion_handlers.py` |

`server.py` moves to `api/mcp/server.py`; imports updated. Tool decorator
names/schemas byte-identical — diff against Phase 0 baseline.

### Phase 6b — Transaction boundary bug fix (separate PR from 6a)

1. `domains/suggestion/service.py.accept_batch(ids)` /
   `reject_batch(ids)` implement the per-item SAVEPOINT loop currently
   inlined in `dashboard/routes/suggestions.py:batch_suggestions` (lines
   137-199), using `Database.transaction()` from Phase 5.
2. `dashboard/routes/suggestions.py` calls
   `suggestion_service.accept_batch(...)`/`reject_batch(...)` instead of
   touching `svc._conn` directly. Zero `_conn`/`_svc._` reach-through remains
   in `dashboard/routes/*.py` — verify with
   `grep -rn 'svc\._\|_svc\._' src/lorekeeper/dashboard/` returning nothing.
3. Remove `self._conn.commit()` from `ConfigStore.set_override()`/
   `delete_override()` (Phase 2's `platform/config/repository.py`); the
   calling service (`dashboard/routes/config.py`, `suggestions.py`'s
   `trigger_sweep`) already calls `svc.commit()` afterward — confirm every
   call site does, add `.commit()` where missing.

This is the one phase with an intentional, called-out behavior-preserving
bug fix — kept isolated per the pure-refactor-PR convention.

### Phase 7 — Retire the facade

- Delete `services/orchestrator.py` (the temporary facade from Phase 5).
- `api/mcp/server.py`'s `init_service()` constructs the five domain services
  directly and exposes them via a lightweight `ServiceRegistry` (or module
  globals, matching the existing `_svc`/`_suggestions_store` pattern) instead
  of one `MemoryService`.
- Every `get_service()` call site (`handlers/*.py`, `dashboard/routes/*.py`)
  updated to call the specific domain service it needs
  (`get_memory_service()`, `get_suggestion_service()`, etc.).
- Delete now-empty `services/` directory.
- Update `CLAUDE.md` architecture section: replace the LKPR-51 store table
  with the final domain/infra/platform tree.

## Verification checklist (every phase)

- [ ] `uv run pytest` — same or higher pass count than Phase 0 baseline
- [ ] `uv run ruff check src tests scripts/` — clean
- [ ] `uv run mypy src` — clean
- [ ] MCP tool schema dump matches Phase 0 baseline exactly (names + input schemas)
- [ ] `git diff --stat` reviewed in full — confirm no unrelated changes snuck in
- [ ] Self-review gate score >= 8 before PR
- [ ] CLAUDE.md updated if the phase changes anything CLAUDE.md documents

## Risk notes

- **Phase 5 is the only phase with real logic risk** — mitigated by 1:1 method
  extraction + line-by-line diff before PR, plus keeping the facade so no
  downstream caller changes simultaneously.
- **Shared SQLite connection across repositories**: the sweep thread already
  uses a second `Database` instance on the same file (WAL mode) — Phase 5's
  `UnitOfWork` must wrap the _existing_ per-thread connection, not introduce
  a new one.
- **`types.yaml` location**: stays at package root since it's loaded by
  relative path from whichever module defines `RelationType` — confirm the
  path resolution still works after `domains/link/models.py` moves.
