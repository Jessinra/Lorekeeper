---
id: LKPR-81
title: lore_pin / lore_unpin — memory pinning for permanent retention
type: feature
sprint: ~
rice_score: ~
filed_by: Akane (daily-ideas cron)
github_issue: 184
filed_date: 2026-06-10
---

# [LKPR-81] `lore_pin` / `lore_unpin` — memory pinning

## Problem

The quality feedback loop is great, but it's reactive — it needs repeated `lore_update` calls to learn "this one matters." There's no explicit "I want this to never disappear" signal. Critical architectural decisions, onboarding configs, and project conventions should be immune to soft-delete and score decay.

## Solution

Add `lore_pin(memory_id)` and `lore_unpin(memory_id)`. Pinned memories:

- Get a score floor (`max(score, 8.0)`) — never decay below high-utility
- Are excluded from soft-delete even with low confidence
- Appear at the top of search results (or receive a score boost)
- Flagged with `pinned: true` in the memory metadata

Implementation: one `pinned` boolean field on the memories table. Modify: scoring formula, soft-delete filter, and search re-ranking. ~40 lines of code.

## Acceptance Criteria

- [ ] `lore_pin(memory_id)` pins a memory — score floor set, excluded from soft-delete
- [ ] `lore_unpin(memory_id)` removes pin, memory returns to normal lifecycle
- [ ] Pinned memories get score boost in search results
- [ ] `pinned: true` flag visible in search/memory output
- [ ] Pin state persists across server restarts
- [ ] Pinning a non-existent memory returns clear error

## Effort

S — one DB field, three small logic changes (scoring, soft-delete filter, search re-ranking).

## Competitor Connection

Nobody in the MCP memory space has pinning. `claude-mem` has no equivalent. `agentmemory` has no equivalent. Pure differentiation — and it makes the quality loop **better** by giving it an explicit boundary for what to protect.

## Required Updates

- **CLAUDE.md**: [ ] document `lore_pin` / `lore_unpin` tools
- **Memory store**: [ ] add `pinned` field to memories table
- **Scoring**: [ ] apply floor `max(score, 8.0)` for pinned memories
- **Soft-delete**: [ ] exclude pinned memories from soft-delete threshold check
- **Search**: [ ] boost pinned results in re-ranking
- **Handlers**: [ ] add `lore_pin` and `lore_unpin` MCP tools