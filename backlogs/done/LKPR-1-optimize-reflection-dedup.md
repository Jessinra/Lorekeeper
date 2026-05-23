---
id: LKPR-1
title: Prevent duplicate reflection on already-processed sessions
type: bug
status: done
priority: low
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-05-21
resolved_date: 2026-05-23
---

# [LKPR-1] Prevent duplicate reflection on already-processed sessions

## Problem
Agents sometimes call `lore_reflect` on a session that has already been processed. The `lore_processed_sessions` API tracks completed session IDs but there is no enforcement — duplicate reflect calls go through silently, creating redundant reflection records.

## Solution
Add a guard in the `lore_reflect` handler: check if `session_id` already exists in the processed-sessions store before inserting a new record. Return a clear error or no-op if already processed.

## Confirmed Root Cause

`submit_reflection` in `orchestrator.py` did **not** check if `session_id` already existed
before proceeding. The flow was:

1. `lore_reflect` (server.py) → `svc.submit_reflection(...)` (orchestrator.py)
2. `submit_reflection` immediately generated a fresh `reflection_id = uuid4()`
3. Called `_store.insert_reflection(...)` → plain `INSERT INTO reflections ...` (no ON CONFLICT guard)
4. Called `_store.upsert_session(...)` → `INSERT ... ON CONFLICT(session_id) DO UPDATE` — idempotent for sessions, but overwrote `reflection_id` with the new UUID

**Result:** every duplicate call created a **new orphaned reflection row** and overwrote the
session's `reflection_id` pointer. The original reflection was permanently orphaned.

`_store.get_session(session_id)` already existed and was the correct guard point.

## Fix Applied
In `orchestrator.py::submit_reflection`, added a check for `self._store.get_session(session_id)`.
If a session row exists, return an idempotent no-op response with `already_processed: True` and
the existing reflection metadata — no new rows are inserted.

## Acceptance Criteria
- [x] Calling `lore_reflect` with an already-processed `session_id` returns a meaningful response (error or idempotent no-op) instead of creating a duplicate
- [x] `lore_processed_sessions` remains the source of truth — no secondary dedup layer needed
- [x] Existing behavior for first-time reflect is unchanged

## Affected Files
- `src/lorekeeper/services/orchestrator.py` — added session ID guard before insert
- `tests/test_orchestrator.py` — added three regression tests

## Dependencies
_None_

## Open Questions
- Idempotent no-op (return existing record) or hard error? Probably no-op is friendlier. ✅ Chose no-op.

## Notes
Not critical — slightly inefficient, not data-corrupting. Root cause is verified and fixed.
