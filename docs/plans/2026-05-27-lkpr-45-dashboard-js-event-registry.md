# LKPR-45 Dashboard JS Event Registry Implementation Plan

> **For implementer:** This is a pure refactor — no visual changes. Every tab should look and behave identically after each task. Verify by loading the dashboard after each task.

**Goal:** Replace fragile cross-module callback wiring with event-based tab registration. Adding a new tab should go from touching 5 files to touching 2 files.

**Architecture:** A 15-line `tab-registry.js` holds a `TABS` array and `registerTab()` function. Each tab module registers itself on import. `tab.js` uses the registry instead of hardcoded `TAB_ORDER` + `registerTabCallbacks`. Cross-module calls use `CustomEvent`. `onclick=` in HTML is replaced by event delegation.

**Tech Stack:** Vanilla JS — ES modules, CustomEvent, event delegation. No new dependencies.

---

### Task 1: Create `tab-registry.js`

**Objective:** A shared registry where tab modules self-register on import, exposing `{ name, load, init }` to `tab.js`.

**Files:**
- Create: `src/lorekeeper/dashboard/static/js/tab-registry.js`

**Implementation:**
```js
// ── Tab registry — tab modules self-register on import ──

const TABS = [];
export function registerTab(config) {
    TABS.push(config);
}
export { TABS };
```

**Verification:** Just confirm the module loads:
```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
node -e "import('./src/lorekeeper/dashboard/static/js/tab-registry.js').then(m => { console.log('OK:', Object.keys(m)) })"
```
(May need `--experimental-vm-modules` — this is a guide; don't block if `node` can't resolve relative paths.)

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/js/tab-registry.js
git commit -m "refactor(lkpr-45): create tab-registry.js for self-registering tabs"
```

---

### Task 2: Refactor `tab.js` — use registry + event delegation

**Objective:** Remove hardcoded `TAB_ORDER`, `registerTabCallbacks`, and `window.switchTab`. Replace with registry-driven tab switching and a click delegation on `.tab-bar`.

**Files:**
- Modify: `src/lorekeeper/dashboard/static/js/tab.js`

**Implementation — replace entire file:**

```js
// ── Tab switching — driven by tab-registry, not hardcoded arrays ──

import { TABS } from "./tab-registry.js";

// Event delegation: one listener on tab-bar replaces all onclick= in HTML
document.querySelector(".tab-bar")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (btn) switchTab(btn.dataset.tab);
});

export function switchTab(name) {
    // Hide all tab-panes
    document.querySelectorAll(".tab-pane").forEach((p) => {
        p.classList.remove("active");
    });
    // Deactivate all tab buttons
    document.querySelectorAll(".tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === name);
    });
    // Show the target pane
    const pane = document.getElementById(`tab-${name}`);
    if (pane) pane.classList.add("active");

    // Find registered tab and call its load() if needed
    const tab = TABS.find((t) => t.name === name);
    if (tab && tab.load) {
        tab.load();
    }
}
```

**Verification:** Load the dashboard in a browser. Tab buttons should work without `onclick=` attributes. No errors in console. Don't worry about individual tab content yet — that's wired in later tasks.

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/js/tab.js
git commit -m "refactor(lkpr-45): tab.js uses registry and event delegation"
```

---

### Task 3: Refactor index.html — remove all onclick= attributes

**Objective:** Replace `onclick=` on every tab button and interactive element with `data-tab` attributes for the tab bar, and data attributes for other controls. Interactive elements that need click handlers will be wired via event delegation in their respective tab modules.

**Files:**
- Modify: `src/lorekeeper/dashboard/static/index.html`

**Changes:**

1. **Tab bar buttons (lines 20-27):** Replace `onclick="switchTab('memories')"` with `data-tab="memories"`:

```html
<nav class="tab-bar">
  <button class="tab active" data-tab="memories">Memories</button>
  <button class="tab" data-tab="detail">Detail</button>
  <button class="tab" data-tab="links">Links</button>
  <button class="tab" data-tab="query">Query</button>
  <button class="tab" data-tab="sessions">Sessions</button>
  <button class="tab" data-tab="config">Config</button>
  <button class="tab" data-tab="backup">Backup</button>
  <button class="tab" data-tab="metrics">Metrics</button>
</nav>
```

2. **Memories tab controls:** Replace all `onclick=` with `data-` attributes:

```html
<!-- Filter clear button (line 38) -->
<button id="mem-filter-clear" class="filter-clear hidden">×</button>

<!-- Time filter buttons (lines 41-44) -->
<button class="time-filter-btn active" data-days="">All</button>
<button class="time-filter-btn" data-days="0">Today</button>
<button class="time-filter-btn" data-days="3">3d</button>
<button class="time-filter-btn" data-days="7">1w</button>

<!-- Sort headers (lines 65-70) — use data-sort attribute -->
<th class="sortable" data-sort="title" id="th-title">Title <span class="sort-arrow"></span></th>
<th class="sortable col-score" data-sort="score" id="th-score">Score <span class="sort-arrow">↓</span></th>
<!-- ... repeat for all sort headers ... -->

<!-- Other controls -->
<button id="btn-show-deleted" class="btn-secondary btn-sm">Show deleted</button>
<button id="btn-refresh-memories" class="btn-ghost btn-sm btn-refresh" title="Refresh memories">
  <span class="refresh-icon">↺</span> Refresh
</button>
```

3. **Detail tab:**
- Replace `onclick=` on "← Memories" button with `data-action="back-to-memories"`
- Replace `onclick=` on edit/cancel/delete buttons with `data-action="edit-memory"` etc.

4. **Links tab:** Replace relation filter `onchange=` with `data-action="filter-links"`

5. **Query tab:**
- The query input has `onkeydown` — replace with `data-action="query-on-keydown"`
- The search button — replace with `data-action="run-query"`

6. **Config tab:**
- `onchange=` on checkboxes → wire via event delegation in config.js
- `oninput=` on number inputs → wire in config.js
- `saveConfig` button → `data-action="save-config"` in its container

7. **Backup tab:**
- All `onclick=` → `data-action=` attributes
- The file input `onchange=` → wire via element ID listener in backup.js

8. **Metrics tab:**
- The refresh button `onclick="loadMetricsFromGlobal()"` → no longer needed, metrics tab's `load()` is driven by the registry.

9. **Remove all `window.*` references from HTML.** The script tag at line 331 stays the same:
```html
<script type="module" src="js/app.js"></script>
```

**After this change, `index.html` has zero `onclick=`, `oninput=`, `onchange=`, `onkeydown=` attributes.** All interactivity is driven by event delegation in JS modules.

**Verification:** The dashboard loads without JS errors. Tab bar navigation works (via event delegation from tab.js). Clicking buttons won't do anything yet (the event handlers haven't been ported to the new pattern) — but no 404s or JS errors.

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/index.html
git commit -m "refactor(lkpr-45): remove all onclick= from index.html, use data- attributes"
```

---

### Task 4: Refactor `app.js` — remove all callback wiring

**Objective:** Remove the cross-module callback registration (`registerTabCallbacks`, `registerDetailCallbacks`, etc.) from `app.js`. Tabs now self-register. Cross-module calls use events.

**Files:**
- Modify: `src/lorekeeper/dashboard/static/js/app.js`

**Implementation — replace entire file:**

```js
// ── Entry point — imports all modules (which self-register) ──

import "./api.js";
import "./utils.js";
import "./state.js";
import "./tab.js";

// Import tab modules — each registers itself on import
import "./backup.js";
import "./config.js";
import "./detail.js";
import "./links.js";
import "./memories.js";
import "./metrics.js";
import "./query.js";
import "./runs.js";
import "./sessions.js";
import "./tab-registry.js";

import { TABS } from "./tab-registry.js";
import { switchTab } from "./tab.js";

// ── Auto-refresh ──

const AUTO_REFRESH_MS = 30_000;
let _autoRefreshTimer = null;

async function triggerRefresh() {
    const btn = document.getElementById("btn-refresh-memories");
    const icon = btn?.querySelector(".refresh-icon");
    if (icon) icon.classList.add("spinning");
    btn?.setAttribute("disabled", "");
    try {
        // Find the active tab and call its load()
        const active = document.querySelector(".tab.active");
        if (active) {
            const name = active.dataset.tab;
            const tab = TABS.find((t) => t.name === name);
            if (tab && tab.load) await tab.load();
        }
    } finally {
        if (icon) icon.classList.remove("spinning");
        btn?.removeAttribute("disabled");
        scheduleAutoRefresh();
    }
}

function scheduleAutoRefresh() {
    clearTimeout(_autoRefreshTimer);
    _autoRefreshTimer = setTimeout(triggerRefresh, AUTO_REFRESH_MS);
}

// ── Init ──

function init() {
    // Keyboard shortcuts
    document.getElementById("q-text")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runQuery();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const ev = new CustomEvent("clear-filter");
            document.dispatchEvent(ev);
        }
        if (
            e.key === "/" &&
            !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)
        ) {
            const activeTab = document.querySelector(".tab.active");
            if (activeTab && activeTab.dataset.tab === "memories") {
                e.preventDefault();
                document.getElementById("mem-filter")?.focus();
            }
        }
    });

    // Init backup (file input listener)
    const backup = TABS.find((t) => t.name === "backup");
    if (backup && backup.init) backup.init();

    // Bootstrap the active tab
    const active = document.querySelector(".tab.active");
    if (active) {
        const name = active.dataset.tab;
        const tab = TABS.find((t) => t.name === name);
        if (tab && tab.load) tab.load();
    }

    // For memories tab: also load links in parallel for link count
    const memTab = TABS.find((t) => t.name === "memories");
    const linksTab = TABS.find((t) => t.name === "links");
    if (memTab && memTab.load && linksTab && linksTab.load) {
        Promise.all([memTab.load(), linksTab.load()]).then(scheduleAutoRefresh);
    }
}

// Export for use by query module (which needs it for keyboard shortcut)
// but NOT exposed on window — kept as a module-level reference
let runQuery = () => {};
export function setRunQuery(fn) { runQuery = fn; }

init();
```

Wait — this still has a circular dependency issue. `app.js` imports `query.js` which needs `runQuery` but `app.js` calls `runQuery` in the keyboard handler. Let me fix this by using an event instead.

Revised `init()`:

```js
function init() {
    // Keyboard shortcuts — use events instead of direct function reference
    document.getElementById("q-text")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            document.dispatchEvent(new CustomEvent("run-query"));
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            document.dispatchEvent(new CustomEvent("clear-filter"));
        }
        if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
            const activeTab = document.querySelector(".tab.active");
            if (activeTab && activeTab.dataset.tab === "memories") {
                e.preventDefault();
                document.getElementById("mem-filter")?.focus();
            }
        }
    });

    // Init each tab
    for (const tab of TABS) {
        if (tab.init) tab.init();
    }

    // Bootstrap: load memories + links eagerly for link count in header
    Promise.all(
        TABS.filter((t) => ["memories", "links"].includes(t.name))
            .map((t) => t.load?.())
    ).then(scheduleAutoRefresh);
}
```

Much cleaner. Each tab's `init()` sets up its own event listeners, tab bar delegation is in `tab.js`, and keyboard shortcuts use events.

**Verification:** Dashboard loads without errors. No `window.*` pollution. Auto-refresh timer fires. Keyboard shortcuts still work (Escape, /, Cmd+Enter for query).

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/js/app.js
git commit -m "refactor(lkpr-45): simplify app.js — tabs self-register, no callback wiring"
```

---

### Task 5: Port `memories.js` — self-register + event-driven

**Objective:** Replace callbacks (`registerSelectMemory`) and `window.*` assignments with self-registration via `registerTab` and event emission.

**Files:**
- Modify: `src/lorekeeper/dashboard/static/js/memories.js`

**Implementation changes:**

1. Add imports and self-registration at the top:
```js
import { registerTab } from "./tab-registry.js";

// Replace registerSelectMemory with event-based approach
// When a memory row is clicked, dispatch an event
// Detail module listens for it
```

2. Replace `export function registerSelectMemory(fn)` — delete this entirely.

3. Replace calls to `_selectMemory(id)` with:
```js
document.dispatchEvent(new CustomEvent("memory-selected", { detail: { id } }));
```

4. Replace `window.*` assignments with event delegation:
```js
// Instead of window.onFilterInput = onFilterInput, use delegation:
document.getElementById("mem-filter")?.addEventListener("input", onFilterInput);
```

5. Register the tab:
```js
registerTab({
    name: "memories",
    load: loadMemories,
    init: () => {
        // Wire filter input
        document.getElementById("mem-filter")?.addEventListener("input", onFilterInput);
        // Wire filter clear
        document.getElementById("mem-filter-clear")?.addEventListener("click", clearFilter);
        // Wire time filter buttons (delegation from container)
        document.querySelector(".time-filter-group")?.addEventListener("click", (e) => {
            const btn = e.target.closest(".time-filter-btn");
            if (btn) setTimeFilter(btn, btn.dataset.days);
        });
        // Wire sort headers (delegation from table)
        document.querySelector(".table-wrap")?.addEventListener("click", (e) => {
            const th = e.target.closest("th.sortable");
            if (th) setMemSort(th.dataset.sort);
        });
        // Wire show-deleted button
        document.getElementById("btn-show-deleted")?.addEventListener("click", toggleShowDeleted);
    },
});
```

6. Replace `window.renderList = renderList` with:
```js
// Listen for events that require re-rendering
document.addEventListener("memory-selected", () => renderList());
```

7. Keep `loadMemories`, `renderList`, `clearFilter`, `toggleShowDeleted`, `setMemSort`, `setTimeFilter`, `onFilterInput`, and `updateSortHeaders` as exported functions.

8. Remove ALL `window.* = ...` assignments.

**Verification:** Memories tab loads data. Clicking a memory row navigates to Detail tab. Filter, sort, time buttons all work. Deleted toggle works. Column headers still sort.

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/js/memories.js
git commit -m "refactor(lkpr-45): memories.js self-registers, uses events, no window.*"
```

---

### Task 6: Port `detail.js` — listen for `memory-selected` event

**Objective:** Remove `registerDetailCallbacks` and `window.*`, listen for events instead.

**Files:**
- Modify: `src/lorekeeper/dashboard/static/js/detail.js`

**Implementation changes:**

1. Delete `registerDetailCallbacks()` entirely.

2. Replace the callback pattern with direct imports + event listener:
```js
import { loadMemories } from "./memories.js";
import { loadLinks } from "./links.js";
```

3. Listen for memory-selected event:
```js
document.addEventListener("memory-selected", async (e) => {
    const id = e.detail.id;
    state.setSelectedId(id);
    state.setDetailEditMode(false);
    switchTab("detail");
    // Re-render memory list highlight
    // ... existing selectMemory logic
});
```

4. Replace `_renderDetail` calls — it's already a module-local function.

5. Wire edit/cancel/delete buttons via event delegation in `init()`:
```js
export function init() {
    document.getElementById("detail-page")?.addEventListener("click", (e) => {
        const action = e.target.closest("[data-action]")?.dataset.action;
        if (action === "edit-memory") enterEditMode();
        if (action === "cancel-edit") cancelEditMode();
        if (action === "save-memory") saveMemory();
        if (action === "delete-memory") deleteMemory();
    });
}
```

6. Keep `selectMemory` as exported (it's the event handler) but also keep it callable directly for backward compat during the transition.

7. Remove ALL `window.* = ...` assignments.

**Verification:** Clicking a memory in the Memories tab opens it in Detail tab. Edit/cancel/save/delete buttons work. The "← Memories" button navigates back.

**Commit:**
```bash
git add src/lorekeeper/dashboard/static/js/detail.js
git commit -m "refactor(lkpr-45): detail.js listens for memory-selected event, no callbacks"
```

---

### Task 7: Port remaining tab modules (links, query, config, sessions, backup, metrics, runs)

**Objective:** Each tab module follows the same pattern — self-register via `registerTab`, wire its own event listeners in `init()`, call `load()` on tab switch, remove `window.*` assignments.

**Pattern for each tab (repeat for each file):**

```js
// Template for porting a tab module:
import { registerTab } from "./tab-registry.js";

// ... existing imports and functions ...

registerTab({
    name: "TAB_NAME",
    load: async () => { /* called when tab is activated */ },
    init: () => {
        // Wire module-specific event listeners via delegation
        // Wire data-action handlers
    },
});

// Remove: all register*Callbacks() functions
// Remove: all window.* = ... assignments
// Replace: callback calls with CustomEvent dispatches
```

**Specific per-tab notes:**

- **links.js:** Replace `registerLinksSelectMemory` with event listener for `memory-selected`. Wire relation filter via `init()`.
- **query.js:** Replace `registerQuerySelectMemory` with event listener for `memory-selected`. Listen for `run-query` custom event (dispatched by app.js keyboard handler).
- **config.js:** Wire number input `oninput` and checkbox `onchange` via event delegation in `init()`. Listen for `save-config` data-action clicks.
- **sessions.js:** Simple load-on-activate — just register + load.
- **backup.js:** `initBackup()` → move to `init()` in registration. File input listener stays (already wired by ID). Export/import buttons via delegation.
- **metrics.js:** Load on activate. Refresh button via delegation.
- **runs.js:** Load on activate.

**Verification per tab:** Switch to each tab. Confirm data loads. Confirm all interactive elements work (buttons, checkboxes, inputs, selects, keyboard shortcuts).

**Commit (per file — 7 commits):**
```bash
git add src/lorekeeper/dashboard/static/js/links.js
git commit -m "refactor(lkpr-45): links.js self-registers, uses events"
# ... repeat for each file ...
```

---

### Task 8: Verify all tabs work end-to-end

**Objective:** Full manual QA of the dashboard — confirm zero regressions.

**Verification checklist:**
1. Memories tab: list loads, sort by each column, filter text, time filter buttons, show/hide deleted, refresh
2. Detail tab: click a memory → opens detail, edit fields, cancel, save, delete
3. Links tab: list loads, relation filter, pagination (if any), click link navigates to memory
4. Query tab: type a query, press Enter, results appear, click result → opens detail
5. Sessions tab: list loads, click session → detail view
6. Config tab: values load, change a value → unsaved indicator shows, save → toast confirms
7. Backup tab: export button downloads file, import file picker shows preview, confirm import
8. Metrics tab: chart loads with data
9. Tab switching: all tabs switch cleanly, active state updates
10. Auto-refresh: timer fires, memories list refreshes
11. Keyboard shortcuts: `/` focuses filter, `Escape` clears filter, `Cmd+Enter` runs query
12. No console errors: open DevTools console, confirm zero errors

**If any interaction doesn't work:**
1. Check if the element still has an `onclick=` (missed during porting)
2. Check if the data-action or event listener is correctly wired
3. Check if the event name matches between dispatcher and listener

**Commit:**
```bash
git add -A
git commit -m "refactor(lkpr-45): post-refactor cleanup — all tabs verified"
```

---

### Rollback Plan

If a tab breaks and can't be fixed in 5 minutes:
```bash
git checkout -- src/lorekeeper/dashboard/static/
```
This reverts all dashboard JS/HTML changes. Re-run to confirm original dashboard works, then re-apply with the fix.

The modular structure means each tab is isolated — a bug in `config.js` won't affect `memories.js`. The event-based communication is the only shared dependency, and it's a single 15-line file backed by the browser's built-in `CustomEvent` API.