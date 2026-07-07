# LKPR-101 Implementation Plan — Dashboard Suggestion Review Tab

**Ticket:** LKPR-101 — Dashboard suggestion review tab with accept/reject UI and config panel
**Date:** 2026-06-26
**Status:** Draft

---

## 1. Architecture Overview

The sweep engine (LKPR-99) populates `link_suggestions` with pending candidate pairs. MCP tools (LKPR-100) let agents review them. This ticket adds the **human-facing browser UI**: a Suggestions tab with paginated list, per-item and batch accept/reject, and a sweep config section in the existing Config tab.

**Key constraint:** No LLM calls anywhere. All logic is pure CRUD over `LinkSuggestionStore`.

**Data flow:**

```
[Browser JS] → FastAPI /api/suggestions/* → get_suggestions_store() → LinkSuggestionStore
              FastAPI /api/sweep/*        → get_service().config → ConfigStore overrides
```

The dashboard routes talk directly to `LinkSuggestionStore` (via the `get_suggestions_store()` module-level accessor from `server.py`) — not through `MemoryService`. This preserves the LKPR-100 decision that `MemoryService` does NOT expose `suggestions`.

---

## 2. Backend Changes

### 2.1 New file: `src/lorekeeper/dashboard/routes/suggestions.py`

FastAPI router with these endpoints (matches the ticket spec):

| Method | Path                     | Request                                                     | Response                                                       | Implementation                                                                                                                                                                                                         |
| ------ | ------------------------ | ----------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/suggestions`       | `?limit=50&offset=0&sort_by=score&sort_dir=desc&memory_id=` | `{items: [...], total: int, offset: int}`                      | Calls `get_suggestions_store().get_pending_suggestions()` + manual offset filtering in Python (store doesn't support offset natively; for MVP filter in-memory)                                                        |
| POST   | `/api/suggestions/batch` | `{suggestion_ids: [...], action: "accept"\|"reject"}`       | `{results: [{id, status, message}], accepted: N, rejected: N}` | Iterates IDs, calls `update_suggestion_status()`. On accept: calls `insert_link()` on `LinkStore`, creating a real memory link with `suggested_type` (falls back to `related_to`). On reject: marks status `rejected`. |
| GET    | `/api/suggestions/count` | `?memory_id=`                                               | `{count: N}`                                                   | Calls `count_pending_suggestions()` if no memory_id; otherwise `get_suggestions_for_memory()` + count in Python                                                                                                        |
| POST   | `/api/sweep/trigger`     | (empty)                                                     | `{ok: true}`                                                   | Sets config override `sweep_next_run_at` to current time — scheduler picks it up on next poll (~300s). Non-blocking, no direct sweep call.                                                                             |
| GET    | `/api/sweep/status`      | (empty)                                                     | `{last_run_at: str\|null, next_run_at: str\|null}`             | Reads `sweep_last_run_at` and `sweep_next_run_at` from ConfigStore overrides. Falls back to `last_run_at = next_run_at - interval_hours` if last_run_at not set.                                                       |

**Accept logic detail:** When accepting a suggestion, create a real `memory_links` row:

```python
from lorekeeper.server import get_service, get_suggestions_store
suggestion = get_suggestions_store().get_suggestion(sid)
if suggestion:
    get_service().links.add_link(
        source_memory_id=suggestion.source_memory_id,
        target_memory_id=suggestion.target_memory_id,
        relation_type=suggestion.suggested_type or "related_to",
        reason=f"Accepted from link suggestion sweep",
    )
    get_suggestions_store().update_suggestion_status(sid, "accepted")
```

### 2.2 Modify: `src/lorekeeper/dashboard/app.py`

Add one import and one route registration:

```python
from lorekeeper.dashboard.routes import (
    ...,
    suggestions,  # new
)
...
app.include_router(suggestions.router)
```

### 2.3 Modify: `src/lorekeeper/services/sweep_service.py`

Add one line at the end of `SweepService.run()` to persist last-run timestamp for the dashboard status endpoint:

```python
# After self._conn.commit() at line 184
self._conn.execute(
    "INSERT OR REPLACE INTO config_overrides (key, value) VALUES (?, ?)",
    ("sweep_last_run_at", datetime.now(UTC).isoformat()),
)
self._conn.commit()
```

This is safe because the sweep thread owns its own DB connection.

Note: Need to add `from datetime import UTC, datetime` import if not already present (check). Already has `from datetime import UTC, datetime, timedelta` — no, checking sweep_service.py... it doesn't import datetime at the top. Let me check — `from datetime import UTC, datetime` isn't in sweep_service.py. I'll add it.

### 2.4 No changes to `orchestrator.py`

The dashboard routes talk to `get_suggestions_store()` and `get_service().links` directly. `MemoryService` stays clean.

---

## 3. Frontend Changes

### 3.1 New file: `src/lorekeeper/dashboard/static/js/suggestions.js`

Self-registers as tab `"suggestions"` via `registerTab("suggestions", { load: loadSuggestions })`.

**Functions:**

- `loadSuggestions()` — fetches `GET /api/suggestions`, renders paginated table
- `renderSuggestionRow(s)` — one table row: checkbox + source title (link) + `←→` + target title (link) + score badge (green-tinted by score) + [accept] [reject] buttons
- `acceptSuggestion(id)` / `rejectSuggestion(id)` — calls `POST /api/suggestions/batch` with one ID, removes row on success
- `batchAccept()` / `batchReject()` — collects checked IDs, calls batch endpoint
- `selectAll()` / `selectByMinScore(minScore)` — checkbox helpers
- `navigatePage(delta)` — offset-based pagination (50 per page)

**Pagination:** Store `_offset` and `_total` in module state. Re-fetch on page change.

**Sorting:** Two options in a small `<select>`: "Score ↓" (default), "Age ↑". Passed as `sort_by` query param.

**Color coding:** Score badge background color interpolates between `var(--surface)` (~0.0) and a configurable green `#22c55e` (1.0+):

```js
function scoreColor(score) {
  const intensity = Math.min(score, 1.0);
  return `rgba(34, 197, 94, ${0.1 + intensity * 0.4})`;
}
```

**Title click:** Navigate to Detail tab for that memory:

```js
dispatch("memory:select", { id: suggeston.source_memory_id });
```

### 3.2 Modify: `src/lorekeeper/dashboard/static/index.html`

1. Add **Suggestions tab button** to tab bar:

```html
<button class="tab" data-tab="suggestions" data-testid="tab-suggestions">Suggestions</button>
```

2. Add **Suggestions tab pane** (after Config tab, before Backup tab):

```html
<!-- ══════════════════════════════════════════════════
     Tab: Suggestions
═════════════════════════════════════════════════════ -->
<div id="tab-suggestions" class="tab-pane">
  <div class="panel-controls">
    <span class="item-count" id="suggestions-count"></span>
    <span class="panel-divider"></span>
    <button class="btn-primary btn-sm" data-action="suggestions:accept-selected">
      Accept Selected
    </button>
    <button class="btn-secondary btn-sm" data-action="suggestions:reject-selected">
      Reject Selected
    </button>
    <span class="panel-divider"></span>
    <label><input type="checkbox" id="suggestions-select-all" /> Select all</label>
    <span class="panel-divider"></span>
    <select id="suggestions-sort" data-change="suggestions:sort">
      <option value="score">Sort: Score ↓</option>
      <option value="created_at">Sort: Age ↑</option>
    </select>
    <button class="btn-ghost btn-sm btn-refresh" data-action="suggestions:load" title="Refresh">
      ↺
    </button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th class="col-checkbox"></th>
          <th>Source</th>
          <th class="col-arrow"></th>
          <th>Target</th>
          <th class="col-score">Score</th>
          <th class="col-actions"></th>
        </tr>
      </thead>
      <tbody id="suggestions-rows"></tbody>
    </table>
  </div>
  <div class="pagination-controls" id="suggestions-pagination">
    <span id="suggestions-page-info"></span>
    <button class="btn-ghost btn-sm" data-action="suggestions:prev-page" id="suggestions-prev">
      ‹ Prev
    </button>
    <button class="btn-ghost btn-sm" data-action="suggestions:next-page" id="suggestions-next">
      Next ›
    </button>
  </div>
</div>
```

### 3.3 Modify: `src/lorekeeper/dashboard/static/js/detail.js`

Add a **pending suggestion badge** below the memory header / above the body. After `_renderDetail` renders the detail content, inject:

```js
// After rendering body, before links section
const count = await api("GET", `/api/suggestions/count?memory_id=${m.id}`);
if (count.count > 0) {
  badgeHTML = `<div class="suggestion-badge" data-action="suggestions:navigate" data-memory-id="${m.id}">
      ${count.count} pending suggestion${count.count !== 1 ? "s" : ""} ▸
    </div>`;
}
```

Insert into the detail-content div after the header actions. The badge click dispatches an event that switches to the Suggestions tab filtered for this memory:

```js
document.addEventListener("app:suggestions:navigate", (e) => {
  // Store the memory_id filter, switch to suggestions tab
  state.setSuggestionFilter(e.detail.memoryId);
  switchTab("suggestions");
  dispatch("suggestions:load");
});
```

### 3.4 Modify: `src/lorekeeper/dashboard/static/js/config.js`

Add a **SWEEP section** to the `CFG_FIELDS` object:

```js
sweep: [
    {
        key: "suggest_interval_hours",
        env: "LORE_SUGGEST_INTERVAL_HOURS",
        label: "Sweep interval",
        desc: "Hours between automatic sweeps",
        step: 1,
        type: "int",
    },
    {
        key: "suggest_high_confidence_score",
        env: "LORE_SUGGEST_HIGH_CONFIDENCE_SCORE",
        label: "Auto-accept threshold",
        desc: "Weighted score above which suggestions are tagged 'high confidence'",
        step: 0.01,
        type: "float",
    },
    {
        key: "suggest_ttl_days",
        env: "LORE_SUGGEST_TTL_DAYS",
        label: "Suggestion TTL",
        desc: "Days before unactioned suggestions expire",
        step: 1,
        type: "int",
    },
],
readonly_sweep: [
    {
        key: "sweep_last_run_at",
        env: "SWEEP_LAST_RUN_AT",
        label: "Last sweep",
        desc: "Timestamp of the last completed sweep",
    },
    {
        key: "sweep_next_run_at",
        env: "SWEEP_NEXT_RUN_AT",
        label: "Next scheduled sweep",
        desc: "Timestamp of the next automatic sweep",
    },
],
```

In `loadConfig()`: after the existing sections, render:

```js
document.getElementById("cfg-sweep").innerHTML = CFG_FIELDS.sweep
  .map((f) => _cfgRow(f, cfg[f.key], false))
  .join("");

// Fetch sweep status from /api/sweep/status
const sweepStatus = await api("GET", "/api/sweep/status");
document.getElementById("cfg-sweep-readonly").innerHTML = CFG_FIELDS.readonly_sweep
  .map((f) => _cfgRow(f, sweepStatus[f.key.replace("sweep_", "")] || "—", true))
  .join("");

// Add Run Sweep Now button
document.getElementById("cfg-sweep-actions").innerHTML = `
    <button class="btn-primary btn-sm" data-action="sweep:trigger">Run Sweep Now</button>
`;
```

Add a new `<div class="config-section">` in `index.html` inside the Config tab for sweep:

```html
<div class="config-section">
  <div class="config-section-title">SWEEP</div>
  <div id="cfg-sweep"></div>
  <div id="cfg-sweep-readonly" style="margin-top:12px"></div>
  <div id="cfg-sweep-actions" style="margin-top:12px"></div>
</div>
```

The sweep trigger button event:

```js
document.addEventListener("app:sweep:trigger", async () => {
  await api("POST", "/api/sweep/trigger");
  showToast("Sweep triggered — will run within ~5 minutes");
});
```

### 3.5 Modify: `src/lorekeeper/dashboard/static/css/styles.css`

Add styles for:

- `.suggestion-badge` — small clickable badge in detail view (blue tint, cursor pointer, margin)
- `.col-checkbox` / `.col-arrow` — narrow columns for checkbox and arrow in suggestions table
- `.pagination-controls` — flex row with page info + prev/next
- Score color classes for green tint on high scores in suggestion rows

### 3.6 Modify: `src/lorekeeper/dashboard/static/js/app.js`

Add import:

```js
import "./suggestions.js"; // self-registers
```

---

## 4. Tests

### 4.1 Backend tests in `tests/test_dashboard.py`

Add a new test class `TestSuggestionRoutes` following the existing `fresh_client` / `seeded_client` fixture pattern. The test for suggestions needs seeded suggestion data, so a new fixture `suggestion_client` will:

1. Use `tmp_path` for an isolated DB
2. Call `build_stores()` to create the Stores dataclass with `suggestions` store
3. Seed a few memories (since `link_suggestions` has FK constraints)
4. Insert a few suggestion rows via `stores.suggestions.insert_suggestion()`
5. Initialize `get_suggestions_store()` in server module

Tests:

- `test_get_suggestions_empty` — GET /api/suggestions returns empty list
- `test_get_suggestions_paginated` — GET /api/suggestions?limit=2 returns correct subset + total
- `test_get_suggestions_filter_memory` — GET /api/suggestions?memory_id=X filters correctly
- `test_get_suggestions_count` — GET /api/suggestions/count returns correct total
- `test_batch_accept` — POST /api/suggestions/batch with action=accept creates link, marks accepted
- `test_batch_reject` — POST /api/suggestions/batch with action=reject marks rejected
- `test_sweep_trigger` — POST /api/sweep/trigger returns ok, sets config override
- `test_sweep_status` — GET /api/sweep/status returns timestamps
- `test_get_suggestions_invalid_params` — bad limit/offset returns 422

### 4.2 E2E tests

Add E2E tests for the Suggestions tab in `tests/e2e/`:

- Navigate to Suggestions tab, verify it renders
- Verify count badge works
- Accept/reject suggestion through the UI (interact with browser)

**Note:** E2E tests are excluded from default `pytest` run. They need `playwright install chromium` and `-m e2e` flag.

---

## 5. Implementation Order

| Step | File                    | Description                                  |
| ---- | ----------------------- | -------------------------------------------- |
| 1    | `routes/suggestions.py` | New file with all 5 API endpoints            |
| 2    | `app.py`                | Register new routes module                   |
| 3    | `sweep_service.py`      | Persist `sweep_last_run_at` in `run()`       |
| 4    | `index.html`            | Add Suggestions tab button + pane            |
| 5    | `js/suggestions.js`     | New file — full suggestion tab functionality |
| 6    | `js/detail.js`          | Add pending suggestion badge                 |
| 7    | `js/config.js`          | Add sweep section to config tab              |
| 8    | `index.html`            | Add sweep section HTML to Config tab         |
| 9    | `css/styles.css`        | Suggestion tab styles                        |
| 10   | `js/app.js`             | Import suggestions.js                        |
| 11   | Tests                   | Backend test class + E2E test                |
| 12   | `README.md`             | Document new tab and config options          |

---

## 6. Risks & Mitigations

| Risk                                                                                              | Mitigation                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_suggestions_store()` may not be initialized when dashboard starts before MCP server          | Dashboard's `lifespan` calls `init_service()` which initializes `_suggestions_store`. The routes call `get_suggestions_store()` which raises `RuntimeError` if not initialized — same pattern as MCP tools. |
| Suggest accept creates a memory link — need access to `LinkStore`                                 | Use `get_service().links.add_link()` — `get_service()` is already the dashboard pattern.                                                                                                                    |
| FK constraints on `link_suggestions` require pre-seeded memories in tests                         | Use `_insert_memory` helper pattern from `test_handlers.py`                                                                                                                                                 |
| `LinkSuggestionStore.get_pending_suggestions()` doesn't support offset/pagination natively        | Fetch with larger limit and slice in Python. If DB grows large, add SQL `OFFSET` to `get_pending_suggestions()` in `suggestion_store.py` — trivially backward-compatible with existing callers.             |
| Config tab already has weight/quality/limit/auto-link sections — sweep config adds vertical space | Follow existing config-section pattern. Sweep section goes after auto-link, before readonly.                                                                                                                |

---

## 7. Boundary with LKPR-100

LKPR-100 added MCP tools `lore_get_suggestions` and `lore_review_suggestion`. This ticket adds the **dashboard UI** for the same operations. The underlying `LinkSuggestionStore` is shared — both read/write the same `link_suggestions` table. No code-level coupling between the MCP handlers and dashboard routes; both call store methods independently.

Key difference: LKPR-100's `lore_review_suggestion` takes `action` per-item (`accept`/`reject`) and returns per-item results. This ticket's dashboard batch endpoint takes a uniform action for all submitted IDs. No conflict — they operate on different API layers.
