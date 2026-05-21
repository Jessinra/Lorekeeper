# Plan: API Metrics Tracking + Dashboard Graph

**Goal**: Track every MCP tool call (search, insert, update, reflect, processed_sessions) down to minute granularity, and display a basic usage graph in the dashboard.

## Current Context

- `handlers.py` has `handle_search()`, server.py registers 5 MCP tools: `lore_search`, `lore_insert`, `lore_update`, `lore_reflect`, `lore_processed_sessions`
- `orchestrator.py` has `MemoryService` with `.search()`, `.insert()`, `.update()`, `.submit_reflection()`, `.get_processed_session_ids()`
- `link_store.py` owns SQLite — has schema in `SCHEMA` string, migration framework (`_migrate()`)
- Dashboard is FastAPI + vanilla JS/HTML (no charting libs) at port 7777
- Tabs: Memories, Detail, Links, Query, Sessions, Config, Backup

## Approach

### 1. SQLite table for metrics

Add to `link_store.py` SCHEMA:
```sql
CREATE TABLE IF NOT EXISTS api_metrics (
  minute_bucket  TEXT NOT NULL,   -- ISO minute boundary, e.g. '2026-05-21T14:30:00'
  tool_name      TEXT NOT NULL,   -- 'lore_search', 'lore_insert', etc.
  count          INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (minute_bucket, tool_name)
);
```

Add method: `increment_metric(tool_name: str) -> None` — upserts with `ON CONFLICT DO UPDATE SET count = count + 1`.

Add method: `get_metrics(hours: int = 24) -> list[sqlite3.Row]` — returns rows for the last N hours.

### 2. Increment metrics in `orchestrator.py`

Add `_increment_metric(tool_name: str)` to `MemoryService` which calls `self._store.increment_metric(tool_name)`. Call it at the start of each public method:
- `search()` → `_increment_metric("lore_search")`
- `insert()` → `_increment_metric("lore_insert")`  
- `update()` → `_increment_metric("lore_update")`
- `submit_reflection()` → `_increment_metric("lore_reflect")`
- `get_processed_session_ids()` → `_increment_metric("lore_processed_sessions")`

Also increment on the dashboard REST endpoints that call these methods (since those go through orchestrator too, they'll auto-increment).

### 3. Dashboard REST endpoint

Add to `dashboard/app.py`:
```python
@app.get("/api/metrics")
def get_metrics(hours: int = 24) -> dict:
    store = get_service()._store
    rows = store.get_metrics(hours=hours)
    # Return as list of {minute_bucket, tool_name, count}
    return {"metrics": [dict(r) for r in rows]}
```

### 4. Dashboard UI — new "Metrics" tab

**index.html** — add tab button between Query and Sessions:
```html
<button class="tab" onclick="switchTab('metrics')">Metrics</button>
```

Add tab pane div with:
- Time range selector (1h / 6h / 24h / 7d buttons)
- Sum total at top (total API calls in range)
- Canvas-based chart (line chart: X = time, Y = count, one line per tool)

**JS file**: `static/js/metrics.js`
- Vanilla Canvas 2D line chart — no dependencies
- Fetch `/api/metrics?hours=N`, transform data, draw
- Responsive to tab switching (refresh on tab activate)

**js/app.js** — import and register `metrics.js`

### Files to change

| File | Change |
|------|--------|
| `src/lorekeeper/services/link_store.py` | Add `api_metrics` table to SCHEMA, `increment_metric()`, `get_metrics()` |
| `src/lorekeeper/services/orchestrator.py` | Call `_increment_metric()` in each public method |
| `src/lorekeeper/dashboard/app.py` | Add `GET /api/metrics` endpoint |
| `src/lorekeeper/dashboard/static/index.html` | Add Metrics tab button + pane |
| `src/lorekeeper/dashboard/static/js/metrics.js` | **New file** — fetch + canvas chart |
| `src/lorekeeper/dashboard/static/js/app.js` | Import + wire `metrics.js` |
| `README.md` | Update layout tree, add Metrics tab to dashboard section |

### Tests

- `tests/test_link_store.py` — add test for `increment_metric()` and `get_metrics()`
- Existing tests should pass (no breaking changes — new table via SCHEMA, new column in orchestrator)

### Risks / considerations

- The `minute_bucket` uses UTC ISO format — consistent with the rest of the codebase
- Canvas chart is basic — no zoom, no tooltips. Just a visual overview. Good enough for Jason's "basic graph" requirement.
- Metrics accumulate over time — no cleanup mechanism needed for now (SQLite rows are cheap; a month = ~43k minute buckets × 5 tools = 215k rows, still fast with PRIMARY KEY index)
- No config/env vars needed — it's always on
- Migration: `api_metrics` table goes into SCHEMA which runs on every init — it's a `CREATE TABLE IF NOT EXISTS`, zero-downtime addition

## Step-by-step execution

1. Add `api_metrics` table to `link_store.py` SCHEMA + `increment_metric()` + `get_metrics()`
2. Add `test_link_store_api_metrics` test
3. Add `_increment_metric()` calls to `orchestrator.py`
4. Add `GET /api/metrics` to `dashboard/app.py`
5. Create `dashboard/static/js/metrics.js` with canvas chart
6. Add Metrics tab HTML to `index.html`
7. Wire `metrics.js` in `app.js`
8. Run all tests: `uv run pytest`
9. Update README.md
10. Commit
