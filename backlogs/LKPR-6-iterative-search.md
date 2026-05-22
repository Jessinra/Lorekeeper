---
id: LKPR-6
title: Add lore_search_refine for iterative narrowing of search results
type: feature
status: backlog
priority: high
sprint: 1
rice_score: 42.5  # R:7 I:8 C:85% E:0.5w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-6] Add lore_search_refine for iterative narrowing of search results

## Problem
Current search is one-shot. When results are broad, there's no way to narrow without starting a new query from scratch. Agents lose context between search passes.

## Solution
Extend existing `lore_search` with an optional `refine_from: list[str] | None = None` parameter. When provided, skip the full store fetch and re-rank only within that candidate ID set using the new query.

No new MCP tool — same surface, backward compatible. Agents that don't pass `refine_from` get existing behavior unchanged.

Enables multi-step recall: broad search → narrow to what's relevant. Mirrors how humans actually search memory.

## Acceptance Criteria
- [ ] `lore_search` accepts optional `refine_from: list[str] | None = None`
- [ ] When `refine_from` is provided, only those memory IDs are candidates — no new memories pulled from store
- [ ] When `refine_from` is omitted/None, behavior is identical to current
- [ ] No schema changes required

## Affected Files
- `src/lorekeeper/services/search.py` — add filter-by-ID path before re-ranking
- `src/lorekeeper/handlers.py` — pass `refine_from` through to search service
- `src/lorekeeper/server.py` — add `refine_from` param to `lore_search` tool

## Dependencies
_None_

## Open Questions
- Maximum candidate set size for `refine_from`?

## Notes
Low effort — purely query logic, no schema changes needed. High confidence (85%). Good Sprint 1 quick win.
