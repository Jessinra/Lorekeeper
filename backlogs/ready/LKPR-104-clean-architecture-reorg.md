---
id: LKPR-104
title: Clean architecture reorg — horizontal layers + DDD vertical slices
type: chore
status: S:ready
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Diana (Jason)
filed_date: 2026-07-01
github_issue: 255
---

# [LKPR-104] Clean architecture reorg — horizontal layers + DDD vertical slices

## Problem

`orchestrator.py` (1046 lines) is a god object mixing search, insert, remember,
update, forget, reflection, `import_dump`, and auto-link logic across four
unrelated entities. Two concrete boundary violations already exist:

1. `dashboard/routes/suggestions.py:162-175` executes raw
   `svc._conn.execute("SAVEPOINT ...")` / `ROLLBACK TO` / `RELEASE` — the
   dashboard reaches past the service layer into the orchestrator's private
   connection to get atomic accept/reject.
2. `ConfigStore.set_override()` / `delete_override()` call `self._conn.commit()`
   inline (lines 44, 51) — transaction control leaks into the repository layer,
   contradicting the "orchestrator owns commit control" comment already in
   `orchestrator.py:87`.

There is no consistent horizontal layering (API / service / reusable module /
repository) and no vertical entity boundary (memory / link / suggestion /
reflection are all interleaved in one orchestrator class and one `models.py`).

## Solution

Reorganize into Clean Architecture rings crossed with DDD vertical slices, executed
as 7 phases — each phase its own PR, tests green at every gate, zero MCP API
surface change throughout. Full design rationale and target tree:
`docs/plans/2026-07-01-lkpr-104-clean-architecture-reorg.md`.

Rings (outer -> inner dependency direction, inner ring depends on nothing outer):

- `api/` — MCP handlers + dashboard routes (Interface Adapters)
- `domains/*/service.py` — use-case orchestration, owns transaction boundaries
- `domains/*/{ranking,dedup,feedback,candidate}.py` — pure reusable modules, zero I/O
- `domains/*/repository.py`, `platform/*/repository.py` — CRUD only, no business rules, no inline commit
- `infra/` — SQLite connection, LanceDB engine, BM25 index, scheduler (zero business vocabulary)

Vertical slices: `domains/memory`, `domains/link`, `domains/suggestion`, `domains/reflection`.

No new abstract interfaces/ports are introduced except one: a `UnitOfWork`/
`transaction()` context manager on the database layer — justified because it
fixes finding #1 above, not speculative indirection.

## Acceptance Criteria

- [ ] Phase 0: baseline `pytest`/`ruff`/`mypy` snapshot recorded; MCP tool schema fixture confirmed present
- [ ] Phase 1: `infra/` populated (`database.py`, `search_engine.py`, `keyword_index.py`, `scheduler.py`, `logging_setup.py`, `settings.py`) — pure move
- [ ] Phase 2: `platform/config/repository.py`, `platform/metrics/repository.py` populated — pure move
- [ ] Phase 3: `domains/{memory,link,suggestion,reflection}/repository.py` + `models.py` populated — pure move, `models.py` split by entity
- [ ] Phase 4: `domains/memory/{ranking,dedup,feedback}.py`, `domains/suggestion/{candidate,sweep}.py`, `shared/{serializers,encouragement}.py` populated — pure move
- [ ] Phase 5: `orchestrator.py` split into `domains/{memory,link,suggestion,reflection}/service.py`; `infra/database.py` gains `Database.transaction()` (UnitOfWork); temporary facade in `server.py` preserves existing call sites
- [ ] Phase 6a (mechanical): `handlers.py` split into `api/mcp/handlers/{memory,reflection,suggestion}_handlers.py`
- [ ] Phase 6b (bug fix, separate commit/PR): `dashboard/routes/suggestions.py` uses `suggestion_service.accept_batch()`/`reject_batch()` instead of raw `svc._conn` SAVEPOINT calls; `ConfigStore` inline `.commit()` removed
- [ ] Phase 7: temporary facade retired, `orchestrator.py` deleted, callers use domain services directly
- [ ] MCP tool names/schemas byte-identical at every phase (diffed against Phase 0 baseline)
- [ ] Full test suite green + `ruff check src tests scripts/` + `uv run mypy src` clean at every phase gate
- [ ] `CLAUDE.md` architecture section updated to reflect the final domain/infra/platform structure

## Affected Files

**Backend:**

- Nearly every file under `src/lorekeeper/` moves or is split — see the plan
  doc for the full file-by-file mapping per phase.
- `src/lorekeeper/services/orchestrator.py` — deleted at Phase 7, contents
  distributed across `domains/*/service.py` starting Phase 5
- `src/lorekeeper/dashboard/routes/suggestions.py` — transaction boundary
  fixed at Phase 6b
- `src/lorekeeper/services/config_store.py` — inline commit removed at Phase 6b

**Dashboard (if applicable):**

- Route files updated at Phase 7 to import domain services instead of the
  `MemoryService` facade — no behavior change, no template/JS changes

## Dependencies

None — internal restructuring, no functionality change. LKPR-103 (ABC removal,
initial handler extraction) already landed and is the direct predecessor of
this ticket.

## Required Updates

- **CLAUDE.md**: [ ] Replace the "SQLite store decomposition (LKPR-51)" table
  with the final domain/infra/platform structure once Phase 7 lands
- **Skills**: [ ] N/A — no agent-facing MCP changes
- **Backlog**: [ ] N/A

## Open Questions

- None — plan reviewed and approved by Jason before filing.

## Notes

Filed by Diana per Jason's direct instruction to plan and execute phase by
phase. Each phase is a separate PR; Phase 6 is deliberately split into two
PRs (6a mechanical move, 6b transaction-boundary bug fix) to keep the
pure-refactor-PR convention intact — the bug fix must not be bundled with a
mechanical file move.
