---
id: LKPR-129
title: Memories page — toolbar with search/filter, filter chip row, DataTable, pagination, row-click opens detail drawer
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 294
---

# [LKPR-129] Memories page

## Problem

The Memories tab (built in LKPR-76) is a basic table with no search, no filtering, no pagination, and no interaction. Users can't find a specific memory, filter by namespace or score, toggle deleted memories, or click a row for details. As the memory store grows past a few hundred entries, the flat list becomes unusable.

The spec (§3.2) describes a full-featured Memories page with toolbar, filter chips, a sortable DataTable, pagination, and row-click that opens the MemoryDetailDrawer (LKPR-127). The primitives (LKPR-126) and drawer (LKPR-127) are built separately — this ticket wires them together into a complete page.

## Solution

Rebuild the Memories tab as a full-featured page with four sections: toolbar, filter chip row, DataTable, and pagination. API-backed via `GET /api/memories` with pagination and filter params, falling back to the existing `/api/memories` route.

### 1. Toolbar

A horizontal bar at the top of the page with three controls:

| Control             | Type            | Behavior                                                                                                         |
| ------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------- |
| Search input        | Text input      | Debounced 300ms. Sends `q` param to API. Placeholder: "Search memories..."                                       |
| Namespace filter    | Dropdown select | Populated from a `GET /api/namespaces` call. Options: "All" (default) + each namespace. Sends `namespace` param. |
| Show deleted toggle | ToggleSwitch    | When on, includes `include_deleted=true` in API call. Default off.                                               |
| New memory button   | Stub button     | Purple primary button `+ New`. Disabled/placeholder — future scope.                                              |

The search input has a magnifying glass icon on the left. The namespace filter uses a native `<select>` element. All toolbar controls update the URL query params and re-fetch data without a full page reload.

### 2. Filter chip row

A horizontal row of FilterChip components (from LKPR-126) below the toolbar:

| Chip label      | Filter logic                                    |
| --------------- | ----------------------------------------------- |
| All             | No filter (default active)                      |
| Needs review    | `confidence < 5 AND score < 6`                  |
| High confidence | `confidence >= 8 AND score >= 7`                |
| Stale >30d      | `updated_at < now() - 30d AND soft_deleted = 0` |

Only one chip active at a time (mutually exclusive — selecting a chip replaces the previous selection). "All" is the default. Each chip also shows a count in a badge (from FilterChip's `count` prop). The count is obtained from a `GET /api/memories/counts` endpoint that returns counts for each preset filter.

Filter chips are mutually exclusive with the search bar — if a chip is active and the user types a search, the chip deactivates and vice versa. (Or alternatively, filter chips narrow the search scope when search is active — to be decided in implementation.)

### 3. DataTable

A styled HTML table showing:

| Column  | Data field    | Width | Notes                                                                 |
| ------- | ------------- | ----- | --------------------------------------------------------------------- |
| Title   | `title`       | 30%   | Truncated with ellipsis. Clickable row opens detail drawer.           |
| NS      | `namespace`   | 8%    | NamespaceDot + short label.                                           |
| Score   | `score`       | 8%    | ScorePill component.                                                  |
| Conf    | `confidence`  | 8%    | Numeric out of 10 with small bar indicator.                           |
| Uses    | `usage_count` | 6%    | Numeric.                                                              |
| Links   | link count    | 6%    | Number of linked memories, or "—" if zero.                            |
| Updated | `updated_at`  | 12%   | Relative time ("3m ago", "2d ago") for <7d, formatted date otherwise. |

Table styling:

- Header row: `background: #f9fafb`, `font-size: 11px`, `font-weight: 600`, `color: #6b7280`, `text-transform: uppercase`, `letter-spacing: 0.5px`.
- Body rows: `font-size: 13px`, `border-bottom: 1px solid #f3f4f6`.
- Hover: `background: #f5f3ff` (very light purple).
- Clickable rows: `cursor: pointer`.
- Alternate row shading optional, not required.
- Each row has a `data-memory-id` attribute for click handlers.

Sorting: columns are clickable to sort ASC/DESC. Sort indicator arrow (▲/▼) in the header. Sorting sends `sort` and `sort_dir` params to the API. Client-side re-sorting for small pages (<=50 items) if server-side is not available.

### 4. Pagination

A pagination bar below the table:

| Element                 | Description             |
| ----------------------- | ----------------------- | ------------------- | ------ |
| "Showing N-M of K" text | Left-aligned            |
| Page buttons            | Right-aligned: « Prev   | [1] [2] [3] ... [N] | Next » |
| Page size selector      | Dropdown: 25 / 50 / 100 |

Pagination state: `page` (1-indexed), `per_page`. Sent as query params `page` and `per_page`.

Current page button highlighted purple (`#8b5cf6`). Ellipsis for gaps (>3 pages between current and edge). Clicking a page number re-fetches from API.

### 5. Row click → detail drawer

Clicking any row in the DataTable opens the MemoryDetailDrawer (LKPR-127) for that memory. The row click handler extracts the `lore_id` from `data-memory-id` and passes it to the drawer.

### API: GET /api/memories

New paginated API endpoint:

```
GET /api/memories?page=1&per_page=50&q=search&namespace=code&include_deleted=false&filter=needs_review&sort=updated_at&sort_dir=desc
```

Response:

```json
{
  "memories": [
    {
      "lore_id": "uuid",
      "title": "Memory title",
      "namespace": "code",
      "score": 7.5,
      "confidence": 8,
      "usage_count": 12,
      "links_count": 3,
      "updated_at": "2026-07-01T12:00:00Z",
      "created_at": "2026-06-01T12:00:00Z",
      "description": "...",
      "soft_deleted": false
    }
  ],
  "total": 234,
  "page": 1,
  "per_page": 50,
  "total_pages": 5
}
```

If `/api/memories` is not yet implemented, fall back to the existing `/api/memories` route and do client-side pagination/filtering from the full list (acceptable for Phase A with <10K memories).

### Additional endpoint: GET /api/memories/counts

```
GET /api/memories/counts
```

Returns counts for each filter preset to populate the FilterChip badges:

```json
{
  "all": 234,
  "needs_review": 12,
  "high_confidence": 89,
  "stale_30d": 7
}
```

### Empty state

When no memories match the current filter/search: show EmptyState component (LKPR-126) with a search icon, "No memories found" title, and "Try adjusting your search or filters" message.

### Loading state

On initial load and on filter/search changes: show a subtle skeleton loader (three pulsing rows matching the table layout) while the API call is in flight. The skeleton is a `<div>` matching the table's height, with `background: linear-gradient(...)` animated via CSS `@keyframes pulse`.

### URL state

All page state (search query, namespace, deleted toggle, filter chip, page, sort, sort_dir) is reflected in URL query parameters so the page state is shareable/bookmarkable. On page load, the state is read from URL params. On state change, URL is updated via `history.replaceState()` (no navigation).

## Acceptance Criteria

- [ ] Toolbar renders search input (debounced 300ms), namespace dropdown, Show deleted toggle, + New stub
- [ ] Filter chip row renders All, Needs review, High confidence, Stale >30d (mutually exclusive)
- [ ] DataTable renders all 7 columns with correct data types (ScorePill, NamespaceDot, etc.)
- [ ] Table rows are clickable and open MemoryDetailDrawer with the correct memory
- [ ] Pagination bar shows N-M of K, page buttons with ellipsis, page size selector
- [ ] Search, filter, and pagination all trigger API calls and update the table
- [ ] Deleted memories show with strikethrough title and gray styling when toggle is on
- [ ] Empty state renders when no results match
- [ ] Skeleton loader shows during API fetch
- [ ] URL query params reflect page state (search, namespace, page, etc.)
- [ ] Sortable columns (click header to toggle ASC/DESC)
- [ ] `GET /api/memories` supports all filter/sort/pagination params
- [ ] Falls back to `/api/memories` if v2 endpoint is not available
- [ ] Filter chip badges show correct counts from `/api/memories/counts`

## Non-goals

- No full-text highlighting of search terms in results (future enhancement)
- No drag-to-reorder columns
- No batch select (checkbox per row)
- No CSV/JSON export
- No infinite scroll (classic pagination only)
- No WebSocket real-time updates (polling on tab activation is fine)

## Affected Files

**New:**

- `src/lorekeeper/dashboard/static/js/memories-page.js` — main page module: toolbar, table, pagination, state management
- `src/lorekeeper/dashboard/static/css/memories-page.css` — table layout, toolbar, pagination, skeleton styles

**Modified:**

- `src/lorekeeper/dashboard/routes/memories.py` — add `GET /api/memories` (paginated, filtered), `GET /api/memories/counts`, `GET /api/namespaces`
- `src/lorekeeper/services/memory_store.py` — add `paginated_search()` method with filter/sort/pagination support
- `src/lorekeeper/dashboard/static/index.html` — restructure the Memories tab to use the new memories-page.js module

## Dependencies

- **LKPR-126** (ScorePill, NamespaceDot, FilterChip, ToggleSwitch, EmptyState primitives) — used extensively in the memories page
- **LKPR-127** (MemoryDetailDrawer) — row clicks open the detail drawer

Backend: `MemoryStore` needs `paginated_search()` and `counts_by_filter()` methods.

## Required Updates

- **CLAUDE.md**: [ ] Add `static/js/memories-page.js` and `routes/memories` GET endpoints to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Client-side vs server-side sorting for v1? Prefer server-side for scalability, but bad UX if the v2 endpoint isn't ready. Recommendation: v2 endpoint with server-side sorting + client-side fallback.
- Should filter chips AND search be composable (narrow results with both), or mutually exclusive? Spec §3.2 suggests they should compose — a chip selects a preset filter AND the search narrows further. Implement as composable.

## Notes

This ticket wires together LKPR-125 (existing memory table from the web viewer), LKPR-126 (primitives), and LKPR-127 (detail drawer) into a complete page that matches spec §3.2. The API endpoint pattern (v2 with pagination) follows the existing conventions in the dashboard routes while adding filter/sort params.

The skeleton loader and URL state management patterns follow the precedent set by the Metrics tab in the existing dashboard.

## Next

**LKPR-130** — Sessions page (timeline, session drawer, stacked drawer)
