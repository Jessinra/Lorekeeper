---
id: LKPR-49
title: Token-Efficient lore_search format (title-only probe mode)
type: feature
status: S:proposal
priority: P2:medium
sprint: unplanned
rice_score: ~
filed_by: Akane
filed_date: 2026-05-30
---

# [LKPR-49] Token-Efficient lore_search Format (Title-Only Probe Mode)

## Problem

An agent calls `lore_search("agent deployment patterns")` and gets back 3 full memory bodies — ~800 tokens each. For a coding agent, 2,400 tokens of memory content is context budget that could be spent on code. Agents are optimizing for token efficiency, and `lore_search` returns verbose by default — every call costs in tokens AND context space.

With cheaper models (DeepSeek V4-Pro at 75% off) and the MCP stateless protocol (agents connect/disconnect per call), agents will make MORE tool calls, not fewer. The per-call token tax of verbose search results is a binding constraint.

## Solution

Add a `format` parameter to `lore_search` with two modes:

- **`full`** (default, current behaviour) — returns full memory bodies as today
- **`title`** — returns just titles + scores + `lore_id`, no content body. This lets an agent probe with title mode, pick the 1-2 relevant memories, then call again with `full` for those specific IDs.

No LLM summarization or compression — strictly cheaper than the status quo. The agent decides what to fetch in full.

Example flow:

1. Agent calls `lore_search("deployment patterns", format="title")` → gets titles + scores (~50 tokens)
2. Picks the top 2 by `lore_id`
3. Requests `lore_search` for those specific IDs in `full` mode

Total: ~50 + 1,600 = 1,650 tokens instead of 2,400 — and the agent has more control over what it reads in full.

## Acceptance Criteria

- [ ] `lore_search` accepts new optional `format` param: `"full" | "title"` (default: `"full"`)
- [ ] `title` mode returns `lore_id`, `title`, `score` only — no `content` field
- [ ] Backward compatible — existing calls without `format` param return full content
- [ ] No additional LLM calls or summarization — strictly cheaper than current behaviour
- [ ] Existing skills that call `lore_search` continue working unchanged

## Affected Files

**Backend:**

- `src/lorekeeper/schemas.py` — add `format` param to `LoreSearchInput`
- `src/lorekeeper/services/search.py` — branch on format value in search response builder
- `src/lorekeeper/services/orchestrator.py` — pass format through if needed

**Dashboard (if applicable):**

- `_none_` — `format` param is MCP-only, dashboard search already shows what it needs

## Dependencies

_None_ — simple param extension, no blockers.

## Required Updates

- **CLAUDE.md**: [x] N/A — minor, note the new param
- **README.md**: [ ] Update `lore_search` docs to document `format` param
- **Skills**: [ ] `lorekeeper-search` — update to use `format="title"` for quick probes when only titles are needed

## Open Questions

_None._

## Notes

Filed from cron output 2026-05-30. Jason rated this P2 and requested a simplified version — no `summary`/`bullet` formats, no LLM summarization. Just `title` (titles + scores only) and `full` (current behaviour). S-effort change.
