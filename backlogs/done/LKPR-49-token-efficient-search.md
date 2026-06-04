---
id: LKPR-49
title: Token-Efficient lore_search — title mode + ids bulk retrieval
type: feature
sprint: unplanned
rice_score: ~
filed_by: Akane
filed_date: 2026-05-30
updated_date: 2026-06-01
---

# [LKPR-49] Token-Efficient lore_search — Title Mode + IDs Bulk Retrieval

## Problem

An agent calls `lore_search("agent deployment patterns")` and gets back 3 full memory bodies — ~800 tokens each. For a coding agent, 2,400 tokens of memory content is context budget that could be spent on code. Agents are optimizing for token efficiency, and `lore_search` returns verbose by default — every call costs in tokens AND context space.

With cheaper models (DeepSeek V4-Pro at 75% off) and the MCP stateless protocol (agents connect/disconnect per call), agents will make MORE tool calls, not fewer. The per-call token tax of verbose search results is a binding constraint.

## Solution

**Part A — `format` param (title probe)**

Add a `format` parameter to `lore_search`:
- **`full`** (default) — returns full memory bodies as today
- **`title`** — returns just `lore_id`, `title`, `score`. No content body.

**Part B — `ids` param (bulk retrieval)**

Add an `ids` parameter to `lore_search`. When `ids=["uuid1", "uuid2"]` is provided, skip vector/BM25 entirely and do a SQL `SELECT WHERE id IN (...)` lookup. Returns the same result format as a regular search.

Complete two-call workflow:
1. `lore_search("deployment patterns", format="title")` → ~50 tokens, titles + lore_ids
2. Pick top K → `lore_search(ids=["uuid1", "uuid2"])` → full content for exactly those

~1,650 tokens total vs 2,400 upfront. No LLM calls, no new endpoints. Both parts extend the same tool.

## Acceptance Criteria

- [ ] `lore_search` accepts new optional `format` param: `"full" | "title"` (default: `"full"`)
- [ ] `title` mode returns `lore_id`, `title`, `score` only — no `content` field
- [ ] `lore_search` accepts new optional `ids` param: list of `lore_id` strings
- [ ] When `ids` is provided, skip vector/BM25 — SQL lookup only (`SELECT WHERE id IN (...)`)
- [ ] `ids` lookup returns same result schema as regular search (full content by default)
- [ ] Backward compatible — existing calls without `format` or `ids` behave unchanged
- [ ] No additional LLM calls or summarization
- [ ] Existing skills that call `lore_search` continue working unchanged

## Affected Files

**Backend:**

- `src/lorekeeper/schemas.py` — add `format` and `ids` params to `LoreSearchInput`
- `src/lorekeeper/services/search.py` — branch on format; add SQL ids-lookup path
- `src/lorekeeper/services/orchestrator.py` — pass both params through

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_ — simple param extensions, no blockers.

## Required Updates

- **CLAUDE.md**: [x] N/A — minor, note the new params
- **README.md**: [ ] Update `lore_search` docs to document `format` and `ids` params
- **Skills**: [ ] `lorekeeper-search` — update to use `format="title"` for quick probes; document ids bulk-retrieval pattern

## Open Questions

_None._

## Notes

Filed from cron output 2026-05-30. `format` param: Jason rated P2, simplified to title+full only (no LLM modes). `ids` param: added 2026-06-01 from daily-ideas cron — completes the two-call workflow. Jason direction: extend existing ticket. Bumped to P1 since ids makes the title probe actually useful end-to-end.
