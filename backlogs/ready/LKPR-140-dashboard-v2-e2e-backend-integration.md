---
id: LKPR-140
title: "Dashboard V2 E2E — Full FE/BE Integration Test Suite"
type: chore
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-07-23
github_issue: 0
---

# [LKPR-140] Dashboard V2 E2E — Full FE/BE Integration Test Suite

## Problem

The Playwright suite added in LKPR-137 is broken for all data-driven tests in CI.

`playwright.config.ts` boots `npm run preview`, which serves only the static SvelteKit bundle with no dev proxy. The FastAPI backend (`/api/health`, `/api/memories`, `/api/config`, `/api/links`, `/api/metrics`, etc.) never starts. Every API call fails silently. Pages fall back to their error/empty-state branches. Tests that depend on real rendered data — Home stat tiles, Memory table rows, Settings sections, visual snapshots — cannot pass. The suite gives false confidence.

Additionally, there is no seeded test data. Even if the API were reachable, data-dependent tests would silently skip via their defensive `test.skip()` guards instead of failing loudly.

## Solution

Wire Playwright to a **real running FE+BE stack**:

1. FastAPI backend starts on port 7778 before any test, pointed at a temp isolated `LORE_DATA_DIR`
2. Vite dev server starts on port 7777 and proxies `/api/*` → backend
3. A `globalSetup` script seeds deterministic fixture data (10 memories, 2 links) via the live API before the suite runs
4. Defensive `test.skip()` guards are removed and replaced with hard `expect()` assertions
5. CI gets a new `playwright-dashboard` job that runs the full suite on every push

No backend code changes are required — existing FastAPI routes are already correct.

## Acceptance Criteria

- [ ] `npx playwright test` passes locally when run from `src/dashboard_v2/` with no manually started backend (webServer handles it)
- [ ] Home page: health ring visible, stat tiles show counts > 0 (real data), activity section visible
- [ ] Memories page: table renders rows from seed data, row click opens detail drawer, edit mode activates, drawer actions (edit/delete) are reachable
- [ ] Settings page: all 4 sections render (Search Weights, Scoring, Search & Links, Memory Lifecycle) with values loaded from backend, unsaved indicator fires on field change, save button triggers success toast (real PATCH to /api/config)
- [ ] Shell: nav rail renders all 6 nav items, breadcrumb updates per route, command palette aria-activedescendant updates on ArrowDown, confirm dialog opens and can be cancelled
- [ ] Sessions / Reflections page: timeline renders with 3 seeded reflections (not empty state)
- [ ] Suggestions / Review page: candidates list renders after sweep (not empty state)
- [ ] Visual snapshot tests capture pages in a fully rendered state (not loading/error branches)
- [ ] CI `playwright-dashboard` job is green on a clean push
- [ ] Playwright HTML report + screenshots uploaded as artifact on job failure
- [ ] Zero `test.skip()` guards that exist solely because "no data in test environment"

## Affected Files

**Dashboard V2:**

- `src/dashboard_v2/vite.config.ts` — add `server.proxy: { '/api': { target: 'http://127.0.0.1:7778' } }`
- `src/dashboard_v2/playwright.config.ts` — replace single webServer with two-entry array; add `globalSetup`
- `src/dashboard_v2/tests/global-setup.ts` — new file, seeds memories + links via REST, shells out to seed.py for reflections + suggestions
- `src/dashboard_v2/tests/seed.py` — new file, inserts 3 reflections + runs suggestion sweep via Python processors directly
- `src/dashboard_v2/tests/memories.spec.ts` — remove defensive test.skip guards

**CI:**

- `.github/workflows/ci.yml` — new `playwright-dashboard` job (needs: test; python+node+HF setup; upload artifact on failure)

## Dependencies

- LKPR-137: must be merged first (provides the test files this ticket wires up)

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

_Resolved 2026-07-23 by Jason:_

- ✅ `globalSetup` should also seed reflections and suggestions
- ✅ Chromium-only in CI for now

## Notes

See full implementation plan: `docs/plans/2026-07-23_081656-lkpr-140-dashboard-v2-e2e-backend-integration.md`

The backend starts at port 7778 (not 7777) so Vite dev owns 7777 and can proxy through. Playwright's `baseURL` stays `http://127.0.0.1:7777` — tests don't need to change.

The `HuggingFace model pre-warm` step in CI is required because the dashboard backend initialises the embedding model on startup (same as the existing `e2e` job).
