---
id: LKPR-136
title: Settings Page
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 301
---

# LKPR-136: Settings Page

**Status:** ⬜ Pending | **Depends on:** LKPR-123, LKPR-126 | **Next:** LKPR-137

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The Settings page allows users to tune the sweep engine, ranking weights, auto-linking thresholds, and limits, plus backup/restore data. The v1 dashboard has a config tab but no structured settings page with side-nav and unsaved-changes detection.

## Solution

Build the Settings page with a sticky left side-nav (scroll-spy), single scrolling content column with 6 sections, and a sticky bottom save bar with unsaved-changes indicator. Each section maps to the existing `/api/config` endpoint.

## Acceptance Criteria

- [ ] Sticky left side-nav: General / Scoring & ranking / Auto-linking & duplicates / Limits / Backup & restore / Read-only — scroll-spy highlights active section — per spec §3.8
- [ ] Right side: single scrolling column containing all 6 sections — per spec §3.8
- [ ] Sticky bottom save bar: "Unsaved changes" indicator + Reset / Save buttons — appears once any field changes
- [ ] **General section**: Sweep interval (select), auto-decay toggle, min score threshold, sweep status + "Run sweep now" button — per spec §3.8
- [ ] **Scoring & ranking**: 4 search-weight inputs (Semantic/Keyword/Memory/Usage) each with a proportional bar, live "Σ total" badge (turns red when ≠ 1.00, soft warning only — gap 6.10) — per spec §3.8
- [ ] **Auto-linking & duplicates**: Auto-link toggle, candidates-per-memory (k), confidence floor, duplicate similarity threshold — per spec §3.8
- [ ] **Limits**: Search result limit, max links per memory, decay lambda, confidence window size — per spec §3.8
- [ ] **Backup & restore**: Export tile (include-soft-deleted checkbox, "Export JSON" button, last-export metadata), import tile (drag-and-drop .json, preview diff, "Import" button) — per spec §3.8
- [ ] **Read-only**: Server version, DB path, embedding model (monospace, display-only) — per spec §3.8
- [ ] Save → `PATCH /api/settings`, triggers toast on success
- [ ] Reset → reverts form to server state, no API call
- [ ] Validates types before sending (API does server-side validation, client catches type errors early)

## Components to Build

- `src/dashboard_v2/src/routes/settings.svelte` — page layout with side-nav + scroll content
- `src/dashboard_v2/src/components/settings/SettingsSection.svelte` — reusable section wrapper with title + description
- `src/dashboard_v2/src/components/settings/WeightInput.svelte` — labeled input + proportional bar + live sum check

## API Dependencies

- `GET /api/settings` — exists (/api/config)
- `PATCH /api/settings` — exists (/api/config)
- `POST /api/export` — exists (/api/export)
- `POST /api/import/preview` — exists (/api/import/preview)
- `POST /api/import/confirm` — exists (/api/import/confirm)
- `POST /api/sweep/run` — exists (/api/sweep/trigger)

## Testing

- All 6 sections render correctly
- Field changes show unsaved indicator
- Save works and shows toast
- Weight sum badge turns red when weights ≠ 1.00
- Export triggers file download
- Import preview shows diff counts
- Page matches `design/visuals/page-settings.png`

## Design Ref

- Spec §3.8 (Settings)
- Mockup: `design/visuals/page-settings.png`

## Required Updates

- None — all settings endpoints already exist (`/api/config`, `/api/export`, `/api/import/preview`, `/api/import/confirm`, `/api/sweep/trigger`)

## Design Gaps Resolved

- 6.9 (Persistence): Use persistent config API (already exists)
- 6.10 (Weight validation): Soft warning — flag with color, don't block save

## Next

LKPR-137 — E2E + visual regression tests
