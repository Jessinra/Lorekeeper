---
id: LKPR-80
title: sort_by param on lore_search — sort by recency or frequency
type: feature
status: S:Ready
priority: P2:medium
rice_score: ~
filed_by: Akane (daily-ideas cron)
github_issue: 183
filed_date: 2026-06-10
---

# [LKPR-80] `sort_by` param on `lore_search`

## Problem

Every `lore_search` result is ranked by `combined_score`. There's no way to ask "show me the newest memories about auth" or "what changed most recently?" You'd need a separate timeline tool (LKPR-73) or a recency filter (LKPR-61) — but both are heavier constructs for what could be a single param.

## Solution

Add `sort_by="relevance"|"recent"|"frequent"` to `lore_search`:

- `"relevance"` (default) — current behavior, combined_score ranking
- `"recent"` — sort by `updated_at DESC`
- `"frequent"` — sort by `usage_count DESC`

One param, one conditional ORDER BY branch in the re-ranking step. The recency filter (LKPR-61) and sort param are orthogonal — filter **then** sort — so they compose naturally.

## Acceptance Criteria

- [ ] `lore_search` accepts `sort_by` parameter
- [ ] `"recent"` returns memories sorted by `updated_at` descending
- [ ] `"frequent"` returns memories sorted by `usage_count` descending
- [ ] `"relevance"` (default) unchanged — full hybrid score ranking
- [ ] Param composes with existing filters (query, ids, limit, min_score)
- [ ] Backward compatible — existing calls without sort_by work identically

## Effort

S — one optional param, ORDER BY branch in the search pipeline. ~20-30 LOC.

## Competitor Connection

`claude-mem` has `timeline` as a separate tool (heavier, more code). `agentmemory` has no sort. Folding sort into search is simpler — same utility, better UX.

## Required Updates

- **CLAUDE.md**: [ ] document `sort_by` param
- **Handlers**: [ ] add param to `lore_search` MCP handler
- **Search service**: [ ] add sort_by branching in result re-ranking
