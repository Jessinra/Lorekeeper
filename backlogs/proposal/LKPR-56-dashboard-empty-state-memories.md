---
id: LKPR-56
title: Dashboard empty state for Memories tab — guide new users
type: feature
sprint: ~
rice_score: 30.0 # R:2 I:9 C:90% E:0.5d
filed_by: Jason → Akane
github_issue: 123
filed_date: 2026-06-03
---

# [LKPR-56] Dashboard empty state for Memories tab — guide new users

## Problem

When a new user opens the dashboard before running the seed prompt, the Memories tab shows a completely empty table — just a header row and zero body rows. No message, no guidance. It looks broken instead of intentional.

Other tabs (Sessions, Metrics, Reflections) already handle this correctly with a `run-empty` message like "No reflections yet — invoke /reflect to create one."

## Solution

Add an empty-state row to `#memory-rows` when the API returns zero results. Show a helpful message that guides the user to the seed prompt or the import feature.

**Message to display:**

```
━━ No memories yet ━━

Lorekeeper starts empty. Give the seed prompt to any
connected agent to populate your first memories:

  "Read your prompt/config files and save key facts
   about yourself using lore_remember or lore_insert."

Or import an existing backup from the Backup tab.
```

**Implementation:**

- **CSS:** Add `.mem-empty` class — same styling as `.run-empty` in `styles.css`
- **JS (`memories.js`):** In the function that renders `#memory-rows`, check `rows.length === 0`. If empty, set innerHTML to a row with `colspan="8"` containing the message above.
- The message spans full width (colspan=8 for 1 status + 7 data columns)
- Matches existing empty-state pattern used by `runs.js`, `sessions.js`, `reflections.js`

## Acceptance Criteria

- [ ] Zero-memory state shows the seed prompt message instead of an empty table
- [ ] Styling matches existing empty-state rows in other tabs
- [ ] Once memories exist (even 1), the normal table renders — no regression
- [ ] Works with filter/search — if filter returns zero results, the empty state says "No memories match your filter" instead (differentiate no-memories vs no-results)

## Affected Files

- `src/lorekeeper/dashboard/static/js/memories.js` — add empty-state check in render function
- `src/lorekeeper/dashboard/static/css/styles.css` — add `.mem-empty` class (if not already covered by `.run-empty`)

## How to test

1. Start dashboard with a fresh data dir (no memories)
2. Open Memories tab → see the guide message instead of empty table
3. Add one memory via `lore_remember` → refresh → normal table renders
4. Filter to a term that matches nothing → "No memories match your filter"

## Dependencies

LKPR-55 must land first (so the seed prompt text in the dashboard matches what setup.sh tells the user).

## Required Updates

- **README.md**: [ ] Nothing needed — this is a JS/CSS-only change
- **Skills**: [ ] None needed
