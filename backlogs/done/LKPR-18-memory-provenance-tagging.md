---
id: LKPR-18
title: Memory Provenance Tagging — source_type on memories
type: feature
status: S:done
priority: P2:medium
rice_score: ~
sprint: ~
filed_by: Hermes
github_issue: 61
filed_date: 2026-05-22
updated_date: 2026-06-18
resolved_date: 2026-06-18
---

# [LKPR-18] Memory Provenance Tagging — source_type on memories

## Problem

Every memory stored by an agent has a source — an observation, a reflection, a conversation, a tool result — but Lorekeeper has no way to tag or filter by it. Two agents writing to the same namespace produce an undifferentiated blob. Humans reviewing memory dumps in the dashboard can't tell what came from where.

## Solution

Add a `source_type` enum to the memory model. Each memory carries a label describing its origin. Retrieval can filter by source type.

## Acceptance Criteria

- [x] `lore_insert` accepts optional `source_type` param (defaults to `observed`)
- [x] `lore_remember` accepts optional `source_type` param (defaults to `observed`)
- [x] `source_type` stored in SQLite metadata and returned in `lore_search` results
- [x] `lore_search` supports optional `source_type` filter param (exact match, single value)
- [x] Existing memories backfilled with `source_type: unknown`
- [x] Schema migration handles existing data without data loss

## Affected Files

**Backend:**

- `src/lorekeeper/services/memory_store.py` — add `source_type` to CRUD helpers
- `src/lorekeeper/models.py` — add `SourceType` Literal type, `source_type` field
- `src/lorekeeper/serializers.py` — add source_type to serialize
- `src/lorekeeper/schemas.py` — add source_type params to input schemas
- `src/lorekeeper/handlers.py` — pass source_type through
- `src/lorekeeper/services/orchestrator.py` — pass source_type in service layer
- `src/lorekeeper/services/search.py` — add source_type filter to query builder
- `src/lorekeeper/services/database.py` — migration to add source_type column
- `tests/test_source_type_provenance.py` — comprehensive test suite

**Dashboard (if applicable):**

- _none_

## Dependencies

_None_

## Notes

Phase B (agent tags / `tags_filter`) split out to LKPR-95.

Shipped in PR #219 (commit d91f6e6). Key design decisions:

- `WRITE_SOURCE_TYPES = SOURCE_TYPES - {"unknown"}` — write-time validation excludes the backfill sentinel
- `Memory.source_type: SourceType` (Literal) instead of `str` — Pydantic + mypy enforce closed enum
- `ON CONFLICT DO UPDATE` includes `source_type=excluded.source_type` — upsert correctly overwrites provenance

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A
- **Skills**: [ ] Update `lorekeeper-search` skill to mention `source_type` filter
- **Backlog**: [ ] N/A
