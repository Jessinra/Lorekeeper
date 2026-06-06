---
id: LKPR-45
github_issue: 83
title: Dashboard JS — replace fragile cross-module wiring with an event-based tab registry
type: enhancement
sprint: 2
rice_score: ~ # TBD: R:5 I:8 C:90% E:0.5w
filed_by: Diana
filed_date: 2026-05-27
---

# [LKPR-45] Dashboard JS — replace fragile cross-module wiring with an event-based tab registry

## Problem

Adding a new tab to the dashboard currently requires touching 5 files:

1. Create the new `.js` module
2. Add tab HTML + tab button in `index.html` (with `onclick=` handler)
3. Add entry to `TAB_ORDER` in `tab.js`
4. Import the module + wire its callbacks in `app.js`
5. If the tab needs data from another module, add a `register*Callbacks()` function

This pattern already exists across 4 modules with different callback names (`registerTabCallbacks`, `registerDetailCallbacks`, `registerSelectMemory`, `registerLinksSelectMemory`, `registerQuerySelectMemory`). Every new tab adds another one.

Additionally, `onclick=` attributes in `index.html` require 14+ functions to be exposed on `window.*` — polluting global scope with implementation details like `runQuery`, `clearFilter`, `saveConfig`, `confirmImport`, etc.

## Solution

Three changes, no new dependencies:

### 1. Event-based cross-module communication

Replace `register*Callbacks()` functions with DOM custom events. Modules emit events like `memory-selected`, `tab-switched`. Any module can listen without explicit wiring.

### 2. Tab self-registration via a shared registry

Each tab module exports a standard `{ name, load, init }` interface and registers itself on import via `registerTab()`. The registry drives `tab.js` instead of hardcoded `TAB_ORDER` + callback arrays.

### 3. Event delegation for UI interactions

Replace `onclick=` attributes on all tab buttons and interactive elements with a single event delegation listener in `tab.js`. This eliminates `window.*` pollution entirely.

## Acceptance Criteria

- [ ] `tab-registry.js` exists with `registerTab()` and `TABS` array
- [ ] Each tab module self-registers on import — no manual wiring in `app.js`
- [ ] `tab.js` uses the registry for tab order and lazy loading — no hardcoded `TAB_ORDER`
- [ ] Cross-module communication uses `CustomEvent` — no `register*Callbacks` functions
- [ ] `index.html` has zero `onclick=` attributes — all interactions use event delegation
- [ ] No `window.*` assignments remain in any `.js` module
- [ ] All existing tabs work identically (Memories, Detail, Links, Query, Sessions, Config, Backup, Metrics)
- [ ] Auto-refresh still fires on the active tab

## Affected Files

- Create: `src/lorekeeper/dashboard/static/js/tab-registry.js`
- Modify: `src/lorekeeper/dashboard/static/js/tab.js`
- Modify: `src/lorekeeper/dashboard/static/js/app.js`
- Modify: `src/lorekeeper/dashboard/static/js/memories.js`
- Modify: `src/lorekeeper/dashboard/static/js/detail.js`
- Modify: `src/lorekeeper/dashboard/static/js/links.js`
- Modify: `src/lorekeeper/dashboard/static/js/query.js`
- Modify: `src/lorekeeper/dashboard/static/js/config.js`
- Modify: `src/lorekeeper/dashboard/static/js/backup.js`
- Modify: `src/lorekeeper/dashboard/static/js/sessions.js`
- Modify: `src/lorekeeper/dashboard/static/js/metrics.js`
- Modify: `src/lorekeeper/dashboard/static/js/runs.js`
- Modify: `src/lorekeeper/dashboard/static/index.html`

## Dependencies

None

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should we keep `state.js` as-is? It works fine and the setters pattern is clear. Leave it.
- Version badge tooling (`_resolve_version` via subprocess)? Not touched — that's backend.
- Should auto-refresh also use events? Yes — that's the simplest path: `triggerRefresh` dispatches `tab-refresh`, active tab responds.

## Notes

No build toolchain changes. This is pure vanilla JS — ES modules, CustomEvent, event delegation. The only new file is a 15-line registry. No regressions in functionality; every tab should feel identical to the user.

Estimated effort: ~3-4 days. Most of the time is porting each tab module, which is mechanical work.
