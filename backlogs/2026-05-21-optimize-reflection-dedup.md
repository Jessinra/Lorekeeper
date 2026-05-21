---
id: LKPR-1
title: Prevent duplicate reflection on already-processed sessions
type: bug
status: backlog
priority: low
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-05-21
---

# [LKPR-1] Prevent duplicate reflection on already-processed sessions

## Problem
Agents sometimes call `lore_reflect` on a session that has already been processed. The `lore_processed_sessions` API tracks completed session IDs but there is no enforcement — duplicate reflect calls go through silently, creating redundant reflection records.

## Solution
Add a guard in the `lore_reflect` handler: check if `session_id` already exists in the processed-sessions store before inserting a new record. Return a clear error or no-op if already processed.

## Acceptance Criteria
- [ ] Calling `lore_reflect` with an already-processed `session_id` returns a meaningful response (error or idempotent no-op) instead of creating a duplicate
- [ ] `lore_processed_sessions` remains the source of truth — no secondary dedup layer needed
- [ ] Existing behavior for first-time reflect is unchanged

## Affected Files
- `src/lorekeeper/handlers.py` — add session ID check before insert
- `src/lorekeeper/services/orchestrator.py` — guard method

## Dependencies
_None_

## Open Questions
- Idempotent no-op (return existing record) or hard error? Probably no-op is friendlier.

## Notes
Not critical — slightly inefficient, not data-corrupting. Root cause is unverified; the guard above is the assumed fix. Verify before implementing.
