---
id: LKPR-73
title: lore_timeline tool — chronological context around any memory
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-08
github_issue: 167
---

# [LKPR-73] lore_timeline tool — chronological context around any memory

## Problem

When an agent finds a relevant memory via `lore_search`, there's no way to understand the **narrative arc** around it — what happened before, what led to it, what came after. The `format='title'` mode gives a list but no temporal framing. This forces agents to individually fetch surrounding memories, which is both wasteful and misses the signal in chronological ordering.

claude-mem solved this with their `timeline()` MCP tool — given an observation ID or query, it returns observations before/after with configurable depth. They report ~10x token savings from their 3-layer workflow (search → timeline → details) vs traditional RAG.

## Solution

Add a new MCP tool `lore_timeline` that takes:

- `anchor_id` (UUID) — center the timeline on this memory
- OR `query` (string) — search for the most relevant memory as anchor
- `before` (int, default 3) — how many memories to show before anchor
- `after` (int, default 3) — how many after anchor
- `include_content` (bool, default false) — whether to include full content or just titles

Returns a chronologically ordered list of memories centered on the anchor, each with: `lore_id`, `title`, `created_at`, `type`, `score`, and optionally `content`.

The tool should work with existing `format='title'` output — IDs from `lore_search` can be passed as `anchor_id`.

## Acceptance Criteria

- [ ] New MCP tool `lore_timeline` registered and documented
- [ ] Accepts `anchor_id` (UUID) as primary anchor
- [ ] Accepts `query` as fallback (auto-selects top search result as anchor)
- [ ] `before`/`after` parameters control depth (default 3 each, max 10 each)
- [ ] Returns chronologically sorted memories with `format='title'`-style compact output by default
- [ ] `include_content=true` returns full memory content
- [ ] Works as the middle step in a 3-layer progressive disclosure workflow (search → timeline → get_observation)
- [ ] Unit tests for ordering, edge cases (anchor at start/end of time), and query fallback
- [ ] Integration test: `lore_search` + `lore_timeline` + `lore_search(ids=...)` in sequence

## Affected Files

**Backend**: `services/search.py` (new method), `handlers.py` (new handler), `schemas.py` (new I/O schema)
**Dashboard**: _none_

## Dependencies

None. Independent of existing backlog items.

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — no protocol changes needed
- **README.md**: [ ] Yes — document new `lore_timeline` tool
- **Skills**: [ ] Yes — update `lorekeeper-search` skill to demonstrate 3-layer workflow
- **Backlog**: [ ] Yes — promote to S:Ready after PM review

## Open Questions

- Should `lore_timeline` be a separate tool or a parameter on `lore_search`? Separate tool keeps surface area clean but adds MCP tool definition tokens. Parameter option: `lore_search(mode='timeline', ...)`. Prefer separate tool for clarity.

## Notes

Inspired by claude-mem's timeline() MCP tool. Their 3-layer workflow (search → timeline → get_observations) claims ~10x token savings over fetching everything upfront. Combined with Lorekeeper's existing `format='title'`, this completes the progressive disclosure story.
