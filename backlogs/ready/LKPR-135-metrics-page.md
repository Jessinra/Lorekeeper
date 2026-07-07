---
id: LKPR-135
title: Metrics Page
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 300
---

# LKPR-135: Metrics Page

**Status:** ⬜ Pending | **Depends on:** LKPR-125, LKPR-126 | **Next:** LKPR-136

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The Metrics page provides operational visibility into MCP tool call volume. Currently there is no dedicated page for this — the v1 dashboard has a metrics tab but no heatmap visualization.

## Solution

Build the Metrics page with a total volume card, a main day×hour heatmap grid with hover tooltips, and per-tool breakdown cards each with a mini heatmap.

## Acceptance Criteria

- [ ] Header: page title + refresh button — per spec §3.7
- [ ] Total volume card: 7d total calls + avg calls/day — per spec §3.7
- [ ] Main heatmap grid: day-rows × hour-columns (24), 5-step color scale (lightest = 0, darkest = max) — per spec §2.10
- [ ] Hover tooltip on heatmap cell: date/hour, per-tool breakdown counts, total — per spec §2.10
- [ ] Per-tool breakdown grid: one card per tool (lore_insert, lore_processed_sessions, lore_recommend_links, lore_reflect, lore_search) — per spec §3.7
- [ ] Each tool card: colored accent border (top), total-calls badge, mini heatmap (non-interactive, smaller)
- [ ] Timezone label from API response (server timezone)

## Components to Build

- `src/dashboard_v2/src/routes/metrics.svelte` — page layout
- `src/dashboard_v2/src/components/ui/ToolBreakdownCard.svelte` — per-tool card with mini heatmap

## API Dependencies

- `GET /api/metrics/tool-calls?hours=168` — returns hourly per-tool call counts for 7 days — **needs enhancement** (existing `/api/metrics` supports up to 24h; extend to 168h with hourly buckets)

## Testing

- Heatmap renders with correct day/hour axis labels
- Tooltip shows on hover
- Per-tool breakdown cards render with mini heatmaps
- Page matches `design/visuals/page-metrics.png`

## Design Ref

- Spec §3.7 (Metrics)
- Spec §2.10 (HeatmapGrid)
- Mockup: `design/visuals/page-metrics.png`

## Required Updates

- `GET /api/metrics/tool-calls?hours=168` — extend existing `/api/metrics` to support 168h range with hourly buckets

## Design Gaps Resolved

- 6.12 (Timezone): Use server timezone from API response

## Next

LKPR-136 — Settings page
