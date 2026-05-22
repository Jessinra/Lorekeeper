---
id: LKPR-18
title: Memory Provenance Tagging
type: feature
status: backlog
priority: medium
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-18] Memory Provenance Tagging

## Problem
Agent retrieves a memory but has no way to know where it came from — was it extracted from a conversation, inferred, manually inserted, or synthesized during consolidation? Without provenance, trust calibration is impossible and there's no audit trail for "how did I come to believe X?"

## Solution
Tag every memory at write time with a `source_type` field:
- `observed` — extracted from conversation
- `inferred` — agent derived it
- `user_stated` — user said it explicitly
- `consolidated` — merged from multiple memories
- `injected` — manually added

Expose `source_type` in retrieval results. Allow agents to filter by source type (e.g. only retrieve `user_stated` memories for high-stakes decisions).

## Acceptance Criteria
- [ ] `lore_insert` accepts optional `source_type` param (defaults to `observed`)
- [ ] `source_type` stored in SQLite metadata and returned in `lore_search` results
- [ ] `lore_search` supports `source_type` filter
- [ ] Existing memories backfilled with `source_type: unknown` or inferred default
- [ ] Schema migration handles existing data without data loss

## Affected Files
- `src/lorekeeper/models.py` — add `source_type` field
- `src/lorekeeper/services/memory_engine.py` — persist at insert time
- `src/lorekeeper/services/search.py` — return + filter on source_type
- `src/lorekeeper/handlers.py` — expose in tool inputs/outputs
- `scripts/migrate_from_json.py` — backfill for existing memories

## Dependencies
_None_

## Open Questions
- Should `source_type` be an enum (strict) or free-string (flexible)?

## Notes
Effort is S — tagging is cheap; the real value is surfacing it cleanly in retrieval. Filed from daily ideas cron output (2026-05-22).
