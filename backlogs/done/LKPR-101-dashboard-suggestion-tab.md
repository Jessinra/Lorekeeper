---
id: LKPR-101
title: Dashboard suggestion review tab — accept/reject UI and config panel
type: feature
status: S:Done
priority: P2:medium
sprint: 4
rice_score: ~
filed_by: Akane
github_issue: 233
filed_date: 2026-06-20
---

# [LKPR-101] Dashboard suggestion review tab — accept/reject UI and config panel

## Problem

The sweep engine (LKPR-99) populates `link_suggestions` with pending candidates, and MCP tools (LKPR-100) let agents review them. But there's no human-friendly way to review suggestions in the browser. Users who prefer visual review over agent-driven workflows have no access.

The dashboard also has no way to configure sweep interval or auto-accept threshold without editing env vars.

## Solution

### 1. New "Suggestions" tab in the dashboard

Add a new tab to the tab bar alongside Memories, Detail, Links, etc.

**Layout:**

```
┌─── Suggestion Review ───────────────────────────────────────┐
│                                                              │
│  [  102 pending suggestions  ]  [Accept Top 20] [Reject All] │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ☐ src_title A ←→ tgt_title B   0.92  [accept] [reject] │ │
│  │ ☐ src_title C ←→ tgt_title D   0.78  [accept] [reject] │ │
│  │ ☐ src_title E ←→ tgt_title F   0.65  [accept] [reject] │ │
│  │ ...                                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│  [Page 1 of 6]  [< Prev] [Next >]                            │
└──────────────────────────────────────────────────────────────┘
```

- Each row: checkbox + source title → target title + weighted score + accept/reject buttons
- Titles are clickable links that open the Detail tab for that memory
- Sorting by score (default) or age
- Batch operations: select all / select by minimum score / accept selected / reject selected
- Pagination (50 per page)
- Color coding: higher score = stronger green tint

### 2. Detail indicators

When viewing a memory in the Detail tab, show a small badge if it has pending suggestions:

```
[Memory: "Auth middleware design"]  [3 pending link suggestions ▸]
```

Clicking the badge navigates to the Suggestions tab filtered for this memory.

### 3. Config panel additions

Add a "Sweep" section to the existing Config tab:

| Key                   | Description                               | Default |
| --------------------- | ----------------------------------------- | ------- |
| Sweep interval        | Hours between automatic sweeps            | 12h     |
| Auto-accept threshold | Score above which links are auto-created  | 0.85    |
| Suggestion TTL        | Days before unactioned suggestions expire | 30 days |
| Last sweep            | (read-only) timestamp                     | —       |
| Run sweep now         | (button) triggers sweep immediately       | —       |

- Config changes persisted via the existing config overrides system
- "Run sweep now" button calls the sweep endpoint / triggers the script
- "Last sweep" shows when the previous sweep completed (read from DB or a sweep log)

### 4. API routes

Backend routes under `/api/suggestions/`:

| Method | Path                     | Description                                |
| ------ | ------------------------ | ------------------------------------------ |
| GET    | `/api/suggestions`       | List pending suggestions (paginated)       |
| POST   | `/api/suggestions/batch` | Batch accept/reject by list of IDs         |
| GET    | `/api/suggestions/count` | Total pending count (+ filtered by memory) |
| POST   | `/api/sweep/trigger`     | Trigger sweep immediately (non-blocking)   |
| GET    | `/api/sweep/status`      | Last sweep timestamp + status              |

## Acceptance Criteria

- [ ] "Suggestions" tab in dashboard tab bar (new JS file `suggestions.js`)
- [ ] Tab shows paginated list of pending suggestions with score, titles, actions
- [ ] Accept/reject buttons work per-suggestion, update UI without full reload
- [ ] Batch accept/reject (select all, accept selected, reject selected)
- [ ] Clicking titles navigates to Detail tab for that memory
- [ ] Detail tab shows badge with pending suggestion count
- [ ] Config tab has Sweep section with interval, threshold, TTL settings
- [ ] "Run sweep now" button in config tab
- [ ] API routes for suggestions and sweep control
- [ ] All existing tests pass; new E2E tests for Suggestions tab
- [ ] No LLM calls anywhere

## Affected Files

**Frontend (new + modified):**

- `src/lorekeeper/dashboard/static/index.html` — add Suggestions tab section
- `src/lorekeeper/dashboard/static/js/suggestions.js` (new) — suggestion list, accept/reject, batch ops
- `src/lorekeeper/dashboard/static/js/detail.js` — pending suggestion badge
- `src/lorekeeper/dashboard/static/js/config.js` — sweep config section
- `src/lorekeeper/dashboard/static/css/styles.css` — suggestion tab styling

**Backend (new + modified):**

- `src/lorekeeper/dashboard/routes/suggestions.py` (new) — API routes for suggestions + sweep control
- `src/lorekeeper/dashboard/app.py` — register new routes
- `src/lorekeeper/services/orchestrator.py` — expose suggestion count and sweep trigger

## Dependencies

- LKPR-99 (link suggestion sweep engine) — provides the `link_suggestions` table and data
- LKPR-100 (MCP tools) — shares the same data, but no direct code dependency (dashboard routes talk to orchestrator directly)

## Required Updates

- **README.md**: [ ] Document new dashboard tab and config options

## Notes

Split from LKPR-98 (combined meta-ticket). Purely client-side + API routes — no MCP changes needed. The "pending count badge on detail view" is a nice-to-have that can be deferred if it complicates the implementation.
