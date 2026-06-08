---
id: LKPR-72
title: Beta release QA — install flow, quickstart walkthrough, dashboard UX audit
type: chore
status: S:Proposal
priority: P1:high
sprint: beta
rice_score: ~
filed_by: PM (Akane)
filed_date: 2026-06-08
github_issue: 165
---

## Problem

Before cutting the beta release, we need real human verification that the install flow, quickstart guide, and dashboard UX don't have friction. What looks clean in a README review can fall apart on an actual clean-machine run. The dashboard has never had a dedicated polish pass — there may be layout glitches, missing hover states, or unlabeled sections.

## Solution

Three-phase QA pass:

### Phase 1 — Install flow QA
On a clean Mac (or clean Hermes profile):
1. `pip install lorekeeper-mcp` → verify version matches latest PyPI
2. `lorekeeper --help` → verify all flags/docs correct
3. `lorekeeper` (run server) → verify it starts, logs are clean, no deprecation warnings
4. `lorekeeper setup` (if applicable) → verify setup.sh equivalent works
5. Connect an MCP client → verify `lore_remember` / `lore_search` work
6. Open dashboard → verify all 4 tabs render
7. `uv run pytest` on installed version → all tests pass
8. Document any friction found and fix it

### Phase 2 — Quickstart walkthrough polish
Read the quickstart guide (`docs/quickstart.md`) end-to-end on a fresh machine:
1. Follow every step literally — note anything ambiguous, missing, or wrong
2. Verify the "2 minutes" claim holds (time yourself)
3. If it takes longer than 2 min, either speed up the flow or update the claim
4. Update quickstart with screenshots / terminal output blocks matching what users actually see
5. Verify the seed prompt text (LKPR-55 output) matches what the quickstart tells users to do

### Phase 3 — Dashboard UX audit
Fresh-eyes pass on the dashboard:
1. **Memories tab**: empty state → populate → search/filter → pagination
2. **Sessions tab**: any lags, missing data, confusing layout
3. **Metrics tab**: charts render, legends readable, responsive
4. **Config tab**: overrides save/display correctly
5. **General**: responsive at tablet width? Mobile? Dark mode consistency? Tab labels clear?
6. **Network tab** in DevTools: any failed requests, slow loads, console errors?
7. File any bugs found as tickets (or inline fixes if trivial)

## Acceptance Criteria

- [ ] Phase 1: Clean install from PyPI works end-to-end, no friction points
- [ ] Phase 1: Any friction found is documented and fixed before beta tag
- [ ] Phase 2: Quickstart followed in < 2 minutes on clean machine
- [ ] Phase 2: Quickstart updated with real terminal output / screenshots
- [ ] Phase 3: Dashboard passes visual audit — no layout bugs, console errors, or missing labels
- [ ] Phase 3: Any dashboard bugs filed as tickets (P1 if broken, P3 if polish)

## Affected Files

- `docs/quickstart.md` — walkthrough update
- `README.md` — if install instructions need updating
- `setup.sh` — if install QA reveals bugs
- `src/lorekeeper/dashboard/` — any trivial fixes found during audit

## Dependencies

- None — can run against any live instance (local or PyPI)

## Required Updates

- [ ] README.md: [ ] If install instructions change
- [ ] Skills: [ ] lorekeeper-dev — add QA findings as pitfalls