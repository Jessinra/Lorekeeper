---
id: LKPR-88
title: Memory health dashboard tab — quality heatmap, retention trends, decay visibility
type: feature
sprint: ~
github_issue: 204
rice_score: ~
filed_by: Akane
filed_date: 2026-06-12
---

# [LKPR-88] Memory health dashboard tab — quality heatmap, retention trends, decay visibility

## Problem

The feedback loop works invisibly. Users can't see their memory getting smarter — they just feel like things work slightly better over time. Invisible improvements don't get shared, don't get tweeted, don't convince holdouts.

Currently the Memories tab shows individual memory rows (score, confidence, usage) and the Metrics tab shows API call activity. Neither answers:

- Is my memory quality improving or degrading over time?
- Which topics/sources have the highest retention?
- How many memories are approaching soft-delete?
- What's the average lifespan of a memory before it decays?

Without this visibility, the "self-improving" claim is abstract. The feedback loop is the moat, but nobody can see it working.

## Solution

A new **Health** dashboard tab with four panels built from existing data (no new collection needed):

### Panel 1: Quality trend line

A 7/14/30-day line chart of average memory score over time. The most important single metric — a steady upward line proves the feedback loop works. Three periods: 7d, 14d, 30d. Each data point is the average score of all active memories at that bucket, computed from `score` + `updated_at` in the memories table.

### Panel 2: Score distribution histogram

A bar chart showing how many memories fall into each score bucket (0-2, 2-4, 4-6, 6-8, 8-10). Overlaid: where soft-deleted memories land. This makes the "feedback loop kills low-quality memories" claim visible.

### Panel 3: Memory retention / decay heatmap

Inspired by the Metrics tab's activity grid but for memory health. Rows = date bucket (daily). Columns = score ranges. Cell color = number of memories in that score range at that date. Shows: "are memories staying high-quality, or drifting into mid-range decay?" A diagonal dark band drifting down-left would signal the loop is failing.

### Panel 4: Decay candidates list

A compact table of memories nearing soft-delete (confidence <= 3, usage_count <= 2) sorted by score ascending. One-click action to jump to detail or manually demote. This replaces the blind "hope decay handles it" with actionable visibility.

**No chart library dependency.** All panels use Canvas 2D or SVG drawn inline (same approach as the existing activity grid in the Metrics tab).

## Acceptance Criteria

- [ ] `/api/health` endpoint returns: score_distribution (buckets), score_trend (daily averages for N days), decay_candidates (memories near soft-delete threshold), summary (total active, avg score, avg confidence, deletion rate)
- [ ] Health tab appears in the nav bar between Config and Backup
- [ ] Quality trend line renders with 7/14/30d toggle
- [ ] Score distribution histogram shows active vs. soft-deleted overlay
- [ ] Decay candidates table is actionable (click → jump to detail)
- [ ] All panels render from existing memory data — no new collection, no new background processes
- [ ] Toggle period on trend line refreshes in-place (no full tab reload)
- [ ] Auto-refreshes on tab activation (same lazy-load pattern as Metrics)

## Non-goals

- No real-time monitoring (polling every 30s is fine, same as Memories tab)
- No e-mail/digest/alert triggers (that's LKPR-46 memory digest scope)
- No prediction or "memory will decay in 3 days" — just show current state
- No chart.js / d3 dependency — hand-drawn canvas only
- No new SQLite tables or metrics columns
- No per-memory edit actions from this tab (use Memories tab for that)

## Affected Files

**New:**

- `src/lorekeeper/dashboard/routes/health.py` — `/api/health` endpoint: score distribution query, score trend aggregation, decay candidate query
- `src/lorekeeper/dashboard/static/js/health.js` — tab module: quality trend (canvas), histogram (canvas), decay candidates table, summary strip

**Modified:**

- `src/lorekeeper/dashboard/static/index.html` — add `<button data-tab="health">Health</button>` in nav bar, add `<div id="tab-health" class="tab-pane">`
- `src/lorekeeper/dashboard/app.py` — register the health router
- `src/lorekeeper/services/memory_store.py` — add aggregation methods: `score_distribution()`, `score_trend(days)`, `decay_candidates()`

## Dependencies

_None_ — works with existing data. The memories table has `score`, `soft_deleted`, `updated_at`, `created_at`, `usage_count`, `confidence` — everything needed.

## Required Updates

- **CLAUDE.md**: [ ] add `routes/health.py` to project map under "Dashboard routes"
- **README.md**: [ ] N/A (dashboard features are documented at the docs site, not in README)
- **Skills**: [ ] `lorekeeper-pm` — note Health tab exists when discussing feedback loop visibility in sprint reviews
- **Backlog**: [ ] N/A

## Open Questions

- Trend data: should `/api/health` compute daily averages from the full memories table, or should we store a daily snapshot job? Full-scan query is cheaper and simpler at Phase A scale (<10K memories). Revisit if performance becomes an issue.
- Decay candidate threshold: confidence <= 3 AND usage_count <= 2 is a guess. Should it be configurable? Or should we just show the bottom-N by combined decay risk score?

## Notes

Filed per Jason's direction: "explore and keep as proposal" after the Memory Quality Heatmap idea was discussed. This proposal consolidates the heatmap concept into a full Health tab with four visualizations, based on the existing Metrics tab's activity-grid architecture.

The existing Metrics tab already proves the pattern works — registration, lazy load, canvas/SVG rendering, summary strip. This is a natural extension.
