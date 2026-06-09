---
id: LKPR-78
github_issue: 178
title: Fill critical MCP backend and high-priority dashboard API test gaps
type: chore
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-06-10
---

# [LKPR-78] Fill critical MCP backend and high-priority dashboard API test gaps

## Problem

Audit (conducted during LKPR-56 PR review) revealed two buckets of untested behaviour:

1. **MCP backend critical** — silent-failure paths in `lore_update`, `lore_forget`,
   `lore_processed_sessions`, and `lore_insert force=True` that could regress
   without any failing test to catch them. The `lore_update` link_feedback path
   was completely unexercised — a bad actor could change link scores in unexpected
   ways without detection.
2. **Dashboard API high-priority** — success and branch-coverage gaps in
   reflection detail, session detail, link creation, `include_deleted` filter,
   and config read-back. The `GET /api/reflections/{id}` success path had zero test
   coverage (only 404 was tested).

## Solution

Single test file `tests/test_lkpr78_critical_coverage.py` with 19 tests across
7 test classes. Uses the existing `build_stores` / `build_service` helpers and
a `FakeEngine` shim that avoids real vector DB calls.

### MCP backend (critical)

- `TestUpdateLinkFeedback` (3) — link_feedback score bump, decrement, unknown ID → errors[]
- `TestUpdateMemoryFeedbackErrors` (1) — unknown memory ID → errors[], not exception
- `TestProcessedSessions` (4) — empty state, reflect round-trip, multiple sessions, idempotency
- `TestForgetMixed` (1) — one real + one fake ID in same call → both `forgotten` and `not_found` populated
- `TestInsertForce` (3) — semantic dedup bypass with lowered threshold; DB UNIQUE constraint behaviour; baseline force=False

### Dashboard API (high-priority)

- `TestReflectionDetailRoute` (1) — `GET /api/reflections/{id}` success; `reflection` + `sessions` keys
- `TestSessionDetailRoute` (2) — `GET /api/sessions/{id}` with linked reflection; without reflection (None)
- `TestCreateLinkTargetNotFound` (1) — `POST /api/links` target-not-found → 404 with "target" in detail
- `TestLinksIncludeDeleted` (2) — soft-deleted endpoint links hidden by default; visible with `?include_deleted=true`
- `TestConfigPersistence` (1) — `PATCH /api/config` persists through `GET` read-back

### Side-finding: force=True + UNIQUE(namespace, title)

`force=True` was intended to bypass dedup for agents that need to override
similarity rejection. The DB `UNIQUE(namespace, title)` index means `force=True`
with an identical title silently fails — error ends up in `errors[]`. Test
`test_force_true_same_title_same_namespace_hits_db_constraint` documents this
behaviour. A **separate ticket** is needed to decide the fix strategy.

## Required Updates

- **Tests**: [x] `tests/test_lkpr78_critical_coverage.py` — 19 tests added
- **Backlog**: [x] This ticket file
- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A

## Acceptance Criteria

- [x] `tests/test_lkpr78_critical_coverage.py` exists with 19 passing tests
- [x] Full test suite passes (266 → 285 passing)
- [x] No new ruff/mypy/biome errors
- [x] `force=True` + DB constraint edge-case is documented (not fixed — separate ticket)
