---
id: LKPR-52
title: Lean simplification pass — transactions, dashboard split, validation
type: chore
sprint: 3
rice_score: ~
filed_by: Diana
github_issue: 102
filed_date: 2026-06-02
---

# [LKPR-52] Lean simplification pass — transactions, dashboard split, validation

## Problem

Three maintainability friction points that slow down every change:

- **Scattered commits (16 `self._conn.commit()` calls across 6 stores)** — no single place controls transaction boundaries. Any multi-store operation (insert + links + reflection) has no atomicity guarantee. Hidden "partial success" bugs.

- **`dashboard/app.py` (423 lines)** — mixes routes for memories, links, search, config, reflections, sessions, backup, and metrics in one file. Every dashboard change touches the same file, increasing merge conflict surface and mental overhead.

- **Duplicated validation logic** — request validation lives partly in `handlers.py`, partly in orchestrator internals, partly ad-hoc in dashboard route bodies. Drift between MCP tool validation and dashboard validation is inevitable.

## Solution

Three mechanical refactors, zero behavior change, in a single PR:

**Phase 1 — Transaction boundaries**
- Remove `self._conn.commit()` from individual store methods
- Add explicit `BEGIN` / `COMMIT` / `ROLLBACK` at the orchestrator level for multi-step flows (insert + links + reflection)
- Keep single-store operations auto-committing via a context manager or explicit wrapper — no abstraction theater, just move the responsibility one level up
- Files: `services/database.py`, `services/memory_store.py`, `services/link_store.py`, `services/reflection_store.py`, `services/config_store.py`, `services/metrics_store.py`, `services/orchestrator.py`

**Phase 2 — Dashboard route split (mechanical)**
- Create `dashboard/routes/__init__.py` + individual route modules per domain
- Keep `app.py` as a thin startup file that mounts routers (< 100 lines)
- No functional change to any endpoint
- Files: `dashboard/app.py`, new `dashboard/routes/{memories,links,search,config,reflections,sessions,backup,metrics}.py`

**Phase 3 — Validation consolidation**
- Extract shared Pydantic request/response schemas into a `schemas/` module
- Make `handlers.py` and `dashboard/routes/` import from the same source
- No schema changes — just relocate and deduplicate
- Files: new `schemas/` module, updated `handlers.py`, updated `dashboard/routes/*.py`

## Acceptance Criteria

- [ ] Phase 1: All `self._conn.commit()` calls removed from store internals. Orchestrator controls transaction scope for insert + reflection flows. All existing tests pass unchanged.
- [ ] Phase 2: `app.py` < 100 lines. Route files exist per domain. All dashboard endpoints return identical responses (verified by existing dashboard tests).
- [ ] Phase 3: Shared validation schemas extracted. No duplicate validation logic in handlers vs dashboard. No observable behavior change.
- [ ] No new classes or modules introduced without a 1-line justification comment explaining what coupling/pain it removes.
- [ ] Pre-commit hooks pass (ruff + pytest) on every commit.

## Affected Files

**Backend:**

- `services/database.py` — remove or centralize auto-commit logic
- `services/memory_store.py` — remove internal commits
- `services/link_store.py` — remove internal commits
- `services/reflection_store.py` — remove internal commits
- `services/config_store.py` — remove internal commits
- `services/metrics_store.py` — remove internal commits
- `services/orchestrator.py` — add explicit transaction boundaries in multi-step flows; surgical cleanup (group sections, extract pure helpers)
- `handlers.py` — import schemas from new shared location

**Dashboard:**

- `dashboard/app.py` — shrink to < 100 lines (startup + router mounting)
- `dashboard/routes/` — 8 new files (memories, links, search, config, reflections, sessions, backup, metrics) + `__init__.py`

**New:**

- `schemas/` — shared Pydantic models for request/response validation

## Dependencies

_None_ — purely mechanical, no feature dependencies.

## Required Updates

- **CLAUDE.md**: [ ] — update build order section if structure changes
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

_None._

## Notes

Filed after discussion with Jason — lean refactor philosophy:
- No new abstraction layers unless they remove clear repeated pain
- Prefer small internal extractions, clear transaction boundaries, mechanical module splits
- Zero API behavior change
- Single PR, phased commits