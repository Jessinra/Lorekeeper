---
id: LKPR-18
title: Memory Provenance Tagging — source_type on memories
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
github_issue: 61
filed_date: 2026-05-22
updated_date: 2026-06-18
resolved_date: 2026-06-18
status: S:done
---

# [LKPR-18] Memory Provenance Tagging — source_type on memories

## Problem

Agents retrieve memories but have no way to know where they came from — was a fact extracted from conversation (`observed`), stated explicitly by the user (`user_stated`), inferred by an agent (`inferred`), merged during consolidation (`consolidated`), or manually added (`injected`)? Without provenance, trust calibration is impossible and there's no audit trail for "how did I come to believe X?"

## Solution

Tag every memory at write time with a `source_type` field stored in SQLite metadata:

- `observed` — extracted from conversation (default)
- `inferred` — agent derived it
- `user_stated` — user said it explicitly
- `consolidated` — merged from multiple memories
- `injected` — manually added

Expose `source_type` in retrieval results. Allow agents to filter by source type (e.g. only retrieve `user_stated` memories for high-stakes decisions).

## Acceptance Criteria

- [x] `lore_insert` accepts optional `source_type` param (defaults to `observed`)
- [x] `lore_remember` accepts optional `source_type` param (defaults to `observed`)
- [x] `source_type` stored in SQLite metadata and returned in `lore_search` results
- [x] `lore_search` supports optional `source_type` filter param (exact match, single value)
- [x] Existing memories backfilled with `source_type: unknown`
- [x] Schema migration handles existing data without data loss

## Affected Files

**Backend:**

- `src/lorekeeper/models.py` — add `source_type` field
- `src/lorekeeper/services/memory_engine.py` — persist at insert time
- `src/lorekeeper/services/search.py` — return + filter on source_type
- `src/lorekeeper/services/database.py` — add migration for metadata column
- `src/lorekeeper/handlers.py` — expose in tool inputs/outputs
- `scripts/migrate_from_json.py` — backfill for existing memories

## Dependencies

_None_

## Open Questions

- Should `source_type` be an enum (strict) or free-string (flexible)? Lean toward enum for v1.

## Notes

Phase B (agent tags / `tags_filter`) split out to LKPR-95.

Shipped in PR #219 (commit d91f6e6). Key design decisions:

- `WRITE_SOURCE_TYPES = SOURCE_TYPES - {"unknown"}` — write-time validation excludes the backfill sentinel
- `Memory.source_type: SourceType` (Literal) instead of `str` — Pydantic + mypy enforce closed enum
- `ON CONFLICT DO UPDATE` includes `source_type=excluded.source_type` — upsert correctly overwrites provenance

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
