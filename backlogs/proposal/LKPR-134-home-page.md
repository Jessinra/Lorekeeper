---
id: LKPR-134
title: Home Page
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 299
---

# LKPR-134: Home Page

**Status:** ⬜ Pending | **Depends on:** LKPR-125, LKPR-126 | **Next:** LKPR-135

## Problem

The Home page is the user's landing dashboard — it needs to show a daily digest of knowledge health, quick stats, and recent activity. Currently the v1 dashboard has no equivalent page.

## Solution

Build the Home page with a greeting header, Knowledge Health card (HealthRing SVG + sub-metrics), a 2×2 grid of navigable stat tiles, and a reverse-chronological activity feed. Each stat tile and health sub-metric is a clickable navigation link to the relevant page.

## Acceptance Criteria

- [ ] Greeting header: "Good {time-of-day}, {user}" + today's date + "here's what happened while you were away" — per spec §3.1
- [ ] Row 1: Knowledge Health card (~324px fixed) beside a 2×2 grid of Stat Tiles:
  - [ ] Pending link reviews → routes to `/review` (Suggestions tab)
  - [ ] Memories going stale → routes to `/review` (Stale tab)
  - [ ] New memories today → routes to `/memories` (ideally pre-filtered)
  - [ ] Links in the graph → routes to `/links`
- [ ] Knowledge Health card: HealthRing (SVG donut, composite score) with "Healthy" status pill, three sub-metric progress bars (Freshness, Confidence, Dup Risk) — per spec §2.10
- [ ] Recent Activity card: reverse-chronological list, each row = colored status dot + rich-text description (bold entity names) + relative timestamp — per spec §3.1
- [ ] Activities seen: memory refreshed, link accepted, session logged, memory flagged stale, backup completed
- [ ] Every health-card sub-metric and every stat tile is a clickable navigation link
- [ ] Activity feed click-through: "link accepted" → Links page, "session logged" → Sessions page, "memory" → Memories page (gap 6.14 resolution)

## Components to Build

- `src/dashboard_v2/src/routes/home.svelte` — page layout
- `src/dashboard_v2/src/components/ui/ActivityFeed.svelte` — activity list component

## API Dependencies

- `GET /api/v2/health` — returns: `{ composite_score, freshness, confidence, dup_risk_score, memories_count, avg_score, total_uses, last_updated_at }` — **needs creation** (new endpoint)
- Activity feed data — can use existing `/api/reflections` or a new `/api/v2/activity` endpoint; mock as fallback

## Testing

- Health ring renders with correct SVG donut proportions
- Stat tiles show correct counts and navigate on click
- Activity feed renders items chronologically
- Page matches `design/visuals/page-home.png`

## Design Ref

- Spec §3.1 (Home)
- Spec §2.10 (HealthRing, StatTile, EmptyState)
- Mockup: `design/visuals/page-home.png`

## Required Updates

- None — this is a new page, no existing code to update

## Design Gaps Resolved

- 6.13 (Digest window): Rolling 24h
- 6.14 (Activity feed click-through): Per event type — navigate to relevant page

## Next

LKPR-135 — Metrics page
