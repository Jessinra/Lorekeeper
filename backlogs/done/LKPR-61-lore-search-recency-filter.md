---
id: LKPR-61
title: Add created_after / updated_after recency filters to lore_search
type: feature
status: S:done
priority: P2:medium
rice_score: ~
filed_by: Akane
github_issue: 132
filed_date: 2026-06-04
updated_date: 2026-06-18
resolved_date: 2026-06-17
---

# [LKPR-61] Add created_after / updated_after recency filters to lore_search

## Problem

`lore_search` has no time dimension. Long-running agentic workflows (e.g. multi-hour sessions as context windows grow) have no way to scope retrieval to "what did I store this session?" or "what changed in the last hour?". The only workarounds today are semantic re-search and hoping recency helps, or grepping by ID — both are fragile and slow.

## Solution

Add two optional ISO 8601 timestamp parameters to `lore_search`:

- `created_after` — only return memories whose `created_at >= value`
- `updated_after` — only return memories whose `updated_at >= value`

Implemented as a WHERE clause filter on the SQLite sidecar before the hybrid scoring pipeline runs. The filter narrows the candidate pool; scoring and ranking are unchanged.

## Acceptance Criteria

- [x] `lore_search(query="...", created_after="2026-06-04T00:00:00")` returns only memories created on or after that timestamp
- [x] `lore_search(query="...", updated_after="2026-06-04T00:00:00")` returns only memories updated on or after that timestamp
- [x] Both params are optional; omitting them preserves existing behaviour exactly
- [x] Both params can be combined with all other existing params (`ids`, `refine_from`, `min_score`, `include_deleted`, etc.)
- [x] Invalid ISO strings return a clear validation error (not a 500)
- [x] MCP schema updated to expose the two new optional fields
- [x] Existing tests still pass; new unit tests cover the filter logic

## Affected Files

**Backend:**

- `src/lorekeeper/services/search.py` — add timestamp pre-filter before candidate fetch
- `src/lorekeeper/services/memory_store.py` — add `created_after`/`updated_after` to the SQLite query helper
- `src/lorekeeper/schemas.py` — add optional fields to `LoreSearchInput`
- `src/lorekeeper/handlers.py` — pass new params through to search service
- `tests/test_search.py` — new test cases for recency filtering

**Dashboard (if applicable):**

- _none_

## Dependencies

_None_

## Notes

Shipped in PR #215 (commit 682b8dc). Combined with LKPR-80 for an efficient single-PR delivery.

## Required Updates

- **CLAUDE.md**: [x] Update `lore_search` param table to document `created_after` and `updated_after`
- **README.md**: [ ] N/A
- **Skills**: [x] Update `lorekeeper-search` skill to mention recency filter option
- **Backlog**: [ ] N/A
