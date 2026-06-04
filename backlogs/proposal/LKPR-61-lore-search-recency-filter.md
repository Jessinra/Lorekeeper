---
id: LKPR-61
title: Add created_after / updated_after recency filters to lore_search
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 132
filed_date: 2026-06-04
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

- [ ] `lore_search(query="...", created_after="2026-06-04T00:00:00")` returns only memories created on or after that timestamp
- [ ] `lore_search(query="...", updated_after="2026-06-04T00:00:00")` returns only memories updated on or after that timestamp
- [ ] Both params are optional; omitting them preserves existing behaviour exactly
- [ ] Both params can be combined with all other existing params (`ids`, `refine_from`, `min_score`, `include_deleted`, etc.)
- [ ] Invalid ISO strings return a clear validation error (not a 500)
- [ ] MCP schema updated to expose the two new optional fields
- [ ] Existing tests still pass; new unit tests cover the filter logic

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

## Required Updates

- **CLAUDE.md**: [ ] Update `lore_search` param table to document `created_after` and `updated_after`
- **README.md**: [ ] N/A
- **Skills**: [ ] Update `lorekeeper-search` skill to mention recency filter option
- **Backlog**: [ ] N/A

## Open Questions

- Should the filter apply before or after the BM25/semantic candidate fetch? Before is cheaper (smaller pool); after is more accurate (full scoring on all candidates, then filter). Recommend before — the use case is scoping, not reranking.
- Timezone handling: accept UTC only, or parse tz-aware strings? Recommend UTC-only with a clear error if offset is present — keeps it simple.

## Notes

Idea sourced from ECC repo analysis (affaan-m/ECC) — identified as a useful pattern for agentic loop workflows. Low implementation complexity (WHERE clause on existing SQLite schema), high utility for sessions that run `lore_insert` heavily and need scoped recall.
