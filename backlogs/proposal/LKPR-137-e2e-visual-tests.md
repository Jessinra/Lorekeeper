---
id: LKPR-137
title: E2E + Visual Regression Tests
type: chore
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 302
---

# LKPR-137: E2E + Visual Regression Tests

**Status:** ⬜ Pending | **Depends on:** LKPR-122 through LKPR-136 | **Next:** _(final ticket)_

## Problem

Without automated E2E + visual regression tests, UI regressions go undetected. Every page must be verified to match the mockup exactly, and core user flows must work end-to-end.

## Solution

Set up Playwright with Chromium at 1440×900 viewport. Write tests for every page: navigation, CRUD flows, drawer open/close, bulk operations. Add visual regression snapshots for each page that fail CI on >0.1% pixel diff.

## Acceptance Criteria

- [ ] Playwright project configured in `dashboard_v2/` with `playwright.config.ts`
- [ ] Test: Nav rail renders all 7 items + Settings, active item highlights
- [ ] Test: Each nav item navigates to its page
- [ ] Test: TopBar shows correct breadcrumb per page
- [ ] Test: Command Palette opens on ⌘K, keyboard navigation works
- [ ] Test: Toast fires on action and auto-dismisses
- [ ] Test: Confirm Dialog opens on destructive action, cancels correctly
- [ ] Test: Memories page loads data table, sorts by column, paginates
- [ ] Test: Memories page opens detail drawer on row click, switches to edit mode
- [ ] Test: Sessions page loads timeline, opens session drawer, stacked drawer works
- [ ] Test: Review page loads both tabs, bulk select + accept works
- [ ] Test: Links table loads data, opens relationship drawer, delete confirms
- [ ] Test: Query page runs query, result list updates inspector
- [ ] Test: Home page loads health ring + stat tiles + activity feed
- [ ] Test: Metrics page heatmap renders, tooltip shows on hover
- [ ] Test: Settings page sections render, field change shows unsaved indicator, save works
- [ ] Visual regression: Screenshot each page and compare against baseline — CI fails on >0.1% pixel diff — per spec requirement "UI must be exact same as mockup"
- [ ] Tests run in CI (can be `npm run test:e2e`)

## Configuration

- `playwright.config.ts` — Chromium, 1440×900 viewport, base URL `http://127.0.0.1:7777/`
- `tests/` directory under `dashboard_v2/`
- Visual baseline stored in `tests/visual-baseline/`

## Dependencies

- Playwright (`npm install -D @playwright/test`)
- Playwright browsers (`npx playwright install chromium`)

## Required Updates

- `package.json` — add `"test:e2e"`, `"test:visual"`, `"test:visual:update"` scripts

## Additional Scripts

- `package.json` scripts:
  - `"test:e2e": "playwright test"`
  - `"test:e2e:ui": "playwright test --ui"`
  - `"test:visual": "playwright test --grep @visual"`
  - `"test:visual:update": "playwright test --grep @visual --update-snapshots"`

## Testing

- Tests pass on clean checkout
- Visual regression catches pixel-level UI drift

## Design Ref

- All page mockups in `design/visuals/*.png`

## Next

_(no next ticket — final ticket in the sequence)_
