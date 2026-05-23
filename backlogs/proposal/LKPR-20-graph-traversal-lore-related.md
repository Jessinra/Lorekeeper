---
id: LKPR-20
title: Add lore_related tool for graph traversal via memory links
type: feature
status: proposal
priority: high
sprint: 1
rice_score: 38.4  # R:8 I:8 C:60% E:1w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-20] Add lore_related tool for graph traversal via memory links

## Problem

Memory links (`MemoryLink`) are stored and queryable via `link_store.links_for_memory()`, but agents have no MCP tool to navigate them. The only way to discover linked memories today is to notice IDs in `lore_search` results and manually re-query — which loses the graph structure entirely.

As the memory graph grows, agent recall becomes query-dependent only. Related concepts that aren't keyword/semantic matches to the query get missed, even if they're explicitly linked. Agents can't "follow a thread" from one memory to adjacent ones.

## Solution

New MCP tool: `lore_related(memory_id, depth, relation_type, limit)` — start at a seed memory, walk the link graph, return connected memories with their link metadata.

- **`memory_id`** (required) — seed node UUID
- **`depth`** (optional, default 1, max 3) — how many hops to traverse
- **`relation_type`** (optional) — filter to a specific link type (e.g. `"related_to"`, `"used_in"`). If omitted, traverse all types.
- **`limit`** (optional, default 20) — max memories to return

**Traversal logic:**
- BFS from seed node
- Follow links bidirectionally (source→target and target→source), matching existing `links_for_memory()` behavior
- At each hop, collect neighbor memory IDs + link metadata (relation_type, reason, score)
- Fetch full memory objects for all collected IDs
- Return as list with `hop_distance` and `link_reason` annotated per result

**Example agent workflow:**
```
lore_search("OAuth flow") → returns memory_id: "abc-123"
lore_related("abc-123", depth=2) → returns token refresh, session management, auth error patterns
```

Enables: broad search → land on a node → explore neighborhood. Complements LKPR-6 (query-driven narrowing) with association-driven expansion.

## Acceptance Criteria

- [ ] `lore_related` accepts `memory_id`, optional `depth` (1–3), optional `relation_type`, optional `limit`
- [ ] Returns list of memory objects annotated with `hop_distance` (int) and `link_reason` (str from MemoryLink.reason)
- [ ] Traversal is BFS, bidirectional, respects depth limit
- [ ] Seed memory itself is NOT included in results
- [ ] If `memory_id` doesn't exist or has no links, returns empty list (no error)
- [ ] `relation_type` filter works — passing `"related_to"` only returns memories connected via that type
- [ ] Registered as MCP tool in `server.py`
- [ ] No schema changes required

## Affected Files

**Backend:**
- `src/lorekeeper/services/link_store.py` — add `get_neighbors(memory_id, depth, relation_type)` traversal method
- `src/lorekeeper/services/orchestrator.py` — add `lore_related()` handler that calls link_store + fetches memory objects
- `src/lorekeeper/handlers.py` — new tool handler
- `src/lorekeeper/server.py` — register tool
- `tests/test_lore_related.py` — new test file

**Dashboard (if applicable):**
_none_ — no UI change needed; link graph visualization is a separate concern

## Dependencies

_None_ — `links_for_memory()` already exists in link_store. No schema changes.

## Open Questions

- Should cycle detection be explicit (visited set) or is the depth cap sufficient guard?
- Should `hop_distance=2` results be scored/ranked by link score, or returned in BFS order?
- Worth adding `lore_related` output to dashboard memory detail view eventually? (out of scope for now)

## Notes

Relation types currently defined in `models.py`: `related_to`, `used_in`, `used_for`, `used_by`, `used_as`.

RICE rationale: R:8 (all agents benefit from richer recall), I:8 (high — unlocks graph-native recall pattern), C:60% (lower confidence — graph traversal UX depends on link density, which is still low), E:1w.

Confidence is 60% not because implementation is hard, but because **link density** is uncertain. If agents aren't creating many links in practice, this tool has less utility. Worth monitoring link counts before investing heavily here.

Pairs naturally with LKPR-6 (lore_search_refine): query-driven zoom in + graph-driven expand out.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
