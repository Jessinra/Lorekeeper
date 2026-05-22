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
New MCP tool: `lore_search_refine(query, refine_from, limit)` where `refine_from` is a list of memory IDs from a prior search. The system re-ranks only within that candidate set using the new query.

Enables multi-step recall: broad search → narrow to what's relevant. Mirrors how humans actually search memory.

## Acceptance Criteria
- [ ] `lore_search_refine` accepts `query` + `refine_from: list[uuid]` + `limit`
- [ ] Returns re-ranked subset of the provided candidate IDs — does not pull new memories from the full store
- [ ] `refine_from` is optional; if omitted, falls back to full search (same as `lore_search`)
- [ ] Registered as an MCP tool in `server.py`
- [ ] No schema changes required

## Affected Files
- `src/lorekeeper/services/search.py` — add filter-by-ID pass
- `src/lorekeeper/handlers.py` — new tool handler
- `src/lorekeeper/server.py` — register tool

## Dependencies
_None_

## Open Questions
- Maximum candidate set size for `refine_from`?

## Notes
Low effort — purely query logic, no schema changes needed. High confidence (85%). Good Sprint 1 quick win.
