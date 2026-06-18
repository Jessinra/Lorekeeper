---
id: LKPR-80
title: sort_by param on lore_search — sort by recency or frequency
type: feature
status: S:done
priority: P2:medium
rice_score: ~
filed_by: Akane (daily-ideas cron)
github_issue: 183
filed_date: 2026-06-10
updated_date: 2026-06-18
resolved_date: 2026-06-17
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

- [x] `lore_search` accepts `sort_by` parameter
- [x] `"recent"` returns memories sorted by `updated_at` descending
- [x] `"frequent"` returns memories sorted by `usage_count` descending
- [x] `"relevance"` (default) unchanged — full hybrid score ranking
- [x] Param composes with existing filters (query, ids, limit, min_score)
- [x] Backward compatible — existing calls without sort_by work identically

## Effort

S — one optional param, ORDER BY branch in the search pipeline. ~20-30 LOC.

## Competitor Connection

`claude-mem` has `timeline` as a separate tool (heavier, more code). `agentmemory` has no sort. Folding sort into search is simpler — same utility, better UX.

## Notes

Shipped in PR #215 (commit 682b8dc). Combined with LKPR-61 for an efficient single-PR delivery.

## Required Updates

- **CLAUDE.md**: [x] document `sort_by` param
- **Handlers**: [x] add param to `lore_search` MCP handler
- **Search service**: [x] add sort_by branching in result re-ranking
