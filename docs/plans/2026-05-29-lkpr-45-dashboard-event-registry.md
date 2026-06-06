# LKPR-45: Dashboard JS Event Registry Plan

**Scope**: Replace fragile cross-module wiring (register\*Callbacks, hardcoded TAB_ORDER,
window.\* pollution, onclick= in index.html) with tab-registry + CustomEvent + delegation.

## Design Summary

Three architectural changes, zero new dependencies:

1. **`tab-registry.js`** — shared module with `registerTab()` and `TABS` array. Each tab
   module calls `registerTab(name, { load, init })` at module-scope import time.
2. **`tab.js` uses registry** — drives tab order and lazy loading from `TABS` instead
   of hardcoded `TAB_ORDER` + callback variables.
3. **Event delegation + CustomEvent** — root-level click handler in `tab.js` replaces
   all `onclick=` in `index.html`. `CustomEvent("memory-selected")` and
   `CustomEvent("memories-changed")` replace `register\*Callbacks()`.

## Task Breakdown

### Task 1: Create `tab-registry.js` (~15 lines)

```js
// ── Tab registry — tab modules self-register on import ──
const TABS = [];

export function registerTab(name, { load, init }) {
  TABS.push({ name, load, init });
}

export function getTabs() {
  return TABS;
}

export function getTab(name) {
  return TABS.find((t) => t.name === name);
}
```

### Task 2: Add event delegation + CustomEvent helpers to `tab.js`

- Add a `_eventDelegate` that catches all clicks on `[data-action]`, `[data-tab]`,
  `[data-memory-id]`, `[data-link-id]`, `[data-sess-detail]`, `[data-run-detail]`, and
  `[data-sort]` elements via a single `document.addEventListener("click", ...)`.
- Expose `dispatchAppEvent(name, detail)` as a module export so all modules can fire
  `memory-selected`, `memories-changed`, `links-changed` without importing CustomEvent
  constructors everywhere.

**Data attribute convention** (replaces onclick=):

| Attribute                      | Action                          |
| ------------------------------ | ------------------------------- |
| `data-tab="memories"`          | Switch to tab                   |
| `data-action="clear-filter"`   | Dispatch action event           |
| `data-action="toggle-deleted"` | Toggle show deleted             |
| `data-action="refresh"`        | Trigger refresh                 |
| `data-action="save-config"`    | Save config                     |
| `data-action="export"`         | Trigger export                  |
| `data-action="confirm-import"` | Confirm import                  |
| `data-sort="field"`            | Sort memories/links             |
| `data-memory-id="uuid"`        | Select memory (renderList rows) |
| `data-link-id="uuid"`          | Delete link from links tab      |
| `data-sess-detail="id"`        | Toggle session detail           |
| `data-run-detail="id"`         | Toggle run detail               |

Additionally, components that need to call functions directly (not via delegation) use
`@click`-style inline listeners in their template literals, attached in JS after the
HTML is inserted. This avoids window.\* entirely.

Actually — inline listeners in template literals break the "no window.\*" rule because
`onclick="selectMemory('${id}')"` requires `window.selectMemory`. The fix:

**For dynamically generated HTML** (template literals in render\* functions): Use `data-*`
attributes and let the delegation catch them. The delegation handler dispatches
CustomEvents with the element's dataset as detail. Each module listens for its own
events.

Example: `renderList()` in memories.js generates `<tr data-memory-id="${m.id}">`.
The delegation handler catches the click, dispatches `memory-selected` with `{id}`.
detail.js listens for `memory-selected` → calls `selectMemory(id)`.

### Task 3: Refactor `tab.js`

Before:

```js
export const TAB_ORDER = ["memories", "detail", "links", ...];
export let _onTabLinks = () => {};
export function registerTabCallbacks({onTabLinks, onTabConfig, ...}) {...}
export function switchTab(name) {
  // toggle classes
  if (name === "links" && !state.linksLoaded) _onTabLinks();
  if (name === "config") _onTabConfig();
  // ...
}
```

After:

```js
import { getTabs, getTab } from "./tab-registry.js";

export function switchTab(name) {
  document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach((t, i) => {
    t.classList.toggle("active", getTabs()[i]?.name === name);
  });
  document.getElementById(`tab-${name}`).classList.add("active");

  // Lazy load via registry
  const tab = getTab(name);
  if (tab?.load) tab.load(); // each tab's load() handles its own lazy logic
}
```

The delegation handler replaces `window.switchTab = switchTab` — tab buttons have
`data-tab="memories"` attributes, handler reads `e.target.closest("[data-tab]")`.

### Task 4: Refactor `app.js`

Before: 14 imports, 9 lines of manual callback wiring

After:

```js
// Imports all tab modules (triggers self-registration) + init
import "./tab-registry.js";
import "./api.js";
import "./utils.js";
import "./tab.js";         // self-attaches delegation listener
import "./memories.js";    // self-registers via registerTab()
import "./detail.js";      // self-registers
import "./links.js";       // self-registers
import "./query.js";       // self-registers
import "./sessions.js";    // self-registers
import "./config.js";      // self-registers
import "./backup.js";      // self-registers
import "./metrics.js";     // self-registers
import "./runs.js";        // self-registers
import * as state from "./state.js";

function init() {
  // Keyboard shortcuts (Escape, /, Cmd+Enter) — unchanged
  initBackup();  // file input listener

  // Bootstrap memories tab
  updateSortHeaders("th-", state.memSort, [...]);

  // Timezone label
  document.getElementById("th-updated_at").innerHTML = `Date <span class="tz-label">${tzLabel}</span> <span class="sort-arrow">↓</span>`;

  // Load memories + links eagerly
  state.setAllMemories(await api("GET", "/api/memories?include_deleted=false"));
  // ... lazy loading via tab registry handles detail load
}
```

Wait — `init()` needs to be async if loadMemories is called in the boot path. Currently
it's sync with `Promise.all`. Let me think...

Actually the new flow: `init` dispatches `initial-load` or just fires the initial
load in `app.js` as before. The memories tab's `load()` function handles the caching.
Actually let me keep `init()` mostly unchanged for the boot path — load memories + links
eagerly, then schedule auto-refresh. The tab registry is just about the switching,
not the boot sequence.

### Task 5: Refactor each tab module

Each tab module:

1. Calls `registerTab()` at module scope
2. Implements `load()` that handles its own lazy-load gate
3. Listens for CustomEvents instead of having callbacks injected
4. Removes all `window.* = ...` assignments
5. Uses `data-*` attributes in template literals instead of `onclick="fn()"`

**memories.js changes:**

- Remove `registerSelectMemory()` and `_selectMemory`
- Add `registerTab("memories", { load: loadMemories })` at module scope... but
  `loadMemories` and `registerTab` are exports, so they're hoisted. However the
  tab registry needs the `load` function to be available at import time.
- Remove window.\* assignments
- Template literals: `onclick="selectMemory('${m.id}')"` → `data-memory-id="${m.id}"`
- Make toggleShowDeleted, onFilterInput, etc. listen to data-action events
- Or better: keep them as exported functions, use delegation to dispatch events that
  tab.js or app.js listens for, which then calls the exported functions

Actually, I need to think about this more carefully. If we remove window.\* entirely,
how do inline things like template-generated HTML with onclick get handled?

**Option A: Event delegation only** — No inline onclick anywhere. Everything goes through
a delegation handler. The delegation handler calls exported functions directly, or
dispatches CustomEvents that modules listen for.

Example for memories.js `renderList()`:

```js
// Template uses data-memory-id instead of onclick
`<tr data-memory-id="${m.id}">...</tr>`;
```

The delegation handler in tab.js:

```js
document.addEventListener("click", (e) => {
  const memRow = e.target.closest("[data-memory-id]");
  if (memRow) {
    e.preventDefault();
    dispatchAppEvent("memory-selected", { id: memRow.dataset.memoryId });
    return;
  }

  const tabBtn = e.target.closest("[data-tab]");
  if (tabBtn) {
    e.preventDefault();
    switchTab(tabBtn.dataset.tab);
    return;
  }

  // ... etc for each data-*
});
```

detail.js listens:

```js
document.addEventListener("app-memory-selected", (e) => {
  selectMemory(e.detail.id);
});
```

This is clean but means lots of CustomEvent listeners. Let me go with this approach.

**Option B: Direct function calls from delegation** — The delegation handler has a
dispatch map that maps data-action values to imported functions. This avoids custom
events for UI actions but keeps CustomEvent for cross-module communication.

Let me go with a hybrid:

- **Event delegation** (single handler in tab.js) maps `data-tab`, `data-action`,
  `data-sort`, `data-memory-id` etc. to function calls
- **CustomEvent** for cross-module: `memory-selected`, `memories-changed`, `links-changed`
- The delegation handler for `data-memory-id` dispatches `memory-selected` CustomEvent
  rather than calling detail.js directly (avoids circular import)
- The delegation handler for `data-action="refresh"` calls triggerRefresh directly
  (it's in app.js)

Actually, let me reconsider. The simpler approach is:

The delegation handler in `tab.js` imports all the functions it needs to route clicks.
This creates a central routing hub that knows about all modules — one file with all
the click-to-function mappings. This is actually simpler than dispatching CustomEvents
for every click and having modules listen for them.

```js
// In tab.js — event delegation router
import { switchTab } from "./tab.js";
import {
  clearFilter,
  toggleShowDeleted,
  setMemSort,
  setNamespaceFilter,
  setTimeFilter,
} from "./memories.js";
import { runQuery } from "./query.js";
// etc.

document.addEventListener("click", (e) => {
  const action = e.target.closest("[data-action]");
  if (action) {
    const cmd = action.dataset.action;
    if (cmd === "clear-filter") {
      clearFilter();
      return;
    }
    if (cmd === "toggle-deleted") {
      toggleShowDeleted();
      return;
    }
    if (cmd === "refresh") {
      triggerRefresh();
      return;
    }
    // etc.
  }
  const tabBtn = e.target.closest("[data-tab]");
  if (tabBtn) {
    switchTab(tabBtn.dataset.tab);
    return;
  }

  const memRow = e.target.closest("[data-memory-id]");
  if (memRow) {
    dispatchAppEvent("memory-selected", { id: memRow.dataset.memoryId });
    return;
  }
  // etc.
});
```

But then tab.js becomes a massive import hub, which is basically what app.js was.
Let me go with CustomEvent for the cross-module stuff (memory-selected) and direct
delegation routing for pure UI actions (clear-filter, refresh, etc.).

Actually, I think the cleanest approach given the constraint "no window.\*" and
"index.html has zero onclick=" is:

1. **tab.js gets a delegation handler** that routes `data-tab` and `data-action` clicks
2. **For dynamic content** (template literals), use `data-` attributes on elements
3. **The delegation handler dispatches CustomEvents** for dynamic content interactions
   (memory-selected, delete-link, etc.)
4. **Each module listens for its own CustomEvents** — detail.js listens for
   `memory-selected`, links.js listens for some events, etc.

This keeps each module self-contained (no import hub) and removes all window.\* pollution.

Let me also think about the "detail.js needs loadMemeries, renderList, loadLinks" problem.
Currently detail.js has `_loadMemeries`, `_renderList`, `_loadLinks` callbacks injected
by app.js. With events:

- After saveMemory, dispatch `memories-changed` → memories.js listens → calls loadMemories()
- After deleteLink, dispatch `memories-changed` + `links-changed`
- After selectMemory, dispatch `memory-selected` → detail.js listens → load detail data

But detail.js also needs to call `_renderList()` to update the selection highlight.
And `switchTab("detail")` to navigate to the detail tab.

Let me handle it:

- `switchTab("detail")` is called by detail.js's selectMemory — it can import switchTab directly
  (already does! detail.js line 4: `import { switchTab } from "./tab.js"`)
- `_renderList()` — detail.js dispatches `memory-selected`, memories.js listens and calls
  its own renderList() to update selection highlight. Or better: detail.js calls
  `document.querySelector("[data-memory-id='...']")` to scroll into view.

Wait, currently `selectMemory` in detail.js does:

1. `state.setSelectedId(id)`
2. `switchTab("detail")`
3. `_renderList()` <- this is the callback to memories.js to highlight the row
4. Fetch detail data via API
5. `_renderDetail(data, false)` <- internal to detail.js

Step 3 requires calling memories.js's renderList. With events, we can do:

- Dispatch `memory-selected` with id
- detail.js listens and runs steps 1, 2, 4, 5
- memories.js listens and runs renderList()

But that means details.js doesn't directly call renderList, it fires an event and
hopes memories.js is listening. That's fine — that's the event-based pattern.

OK, let me keep this plan focused and start implementing. The key design decisions:

1. **tab-registry.js**: registerTab + getTabs + getTab
2. **tab.js**: refactored to use registry + event delegation handler + `dispatchAppEvent()`
3. **Cross-module CustomEvents**: `memory-selected`, `memories-changed`, `links-changed`
4. **Each tab module**: self-registers, no window._, uses data-_ in templates
5. **Dynamic content**: data-\* attributes caught by delegation handler → CustomEvent
6. **app.js**: minimal — just boots the app

Let me implement this step by step.
