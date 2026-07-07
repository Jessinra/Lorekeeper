---
id: LKPR-125
title: Data Table + pagination
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 290
---

# [LKPR-125] Data Table + pagination

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The dashboard v2 has no reusable data table component. Every page that displays tabular data — Memories, Links, Suggestions, Stale (Review), Sessions, Query results — would build its own table, duplicating sort/pagination/selection logic and creating visual inconsistencies.

The design spec (§2.1) defines a single data table pattern used across 5+ pages. It must support:

- Sortable columns with ascending/descending indicators
- Click-to-open-drawer row behavior
- Inline action buttons that don't trigger row clicks
- Optional checkbox column for bulk selection (Review only — bulk pattern is §2.6, built alongside LKPR-131)
- Pagination footer with range label and navigation
- Empty state when no rows match
- Integration with Score Pill, Namespace Dot, and Relation Pill (building the table doesn't include building those primitives — see LKPR-126)

## Solution

### 1. Data Table component (`src/dashboard_v2/src/components/table/DataTable.svelte`)

Generic, typed Svelte 5 component with a flexible column definition API:

**Column definition interface:**

```ts
interface Column<T> {
  key: string; // accessor key or custom value accessor
  label: string; // header display text
  sortable?: boolean; // default false
  sortKey?: string; // custom sort key (defaults to column key)
  width?: string; // optional CSS width (e.g. '120px', '1fr')
  align?: "left" | "center" | "right"; // default 'left'
  render?: (row: T, context: { scoreThreshold: number }) => string | Snippet; // custom cell renderer
}
```

**Props:**

- `columns: Column<T>[]` — column definitions
- `rows: T[]` — data rows for the current page
- `sortColumn: string | null` — controlled sort state (two-way binding via `bind:sortColumn`)
- `sortDirection: 'asc' | 'desc'` — controlled (two-way binding via `bind:sortDirection`)
- `onRowClick: (row: T) => void` — row click handler (opens detail drawer)
- `selectable?: boolean` — show checkbox column (default false; bulk-select wiring is LKPR-131 scope)
- `selectedRows?: Set<string>` — controlled selection state (default empty; LKPR-131)
- `emptyMessage?: string` — override empty state text (default "No rows to display")
- `loading?: boolean` — show loading skeleton state (default false)

**Rendering:**

- **Header row:** sticky (`position: sticky; top: 0`), uppercase 11px muted labels (`micro-size` token), tracking `0.05em`
- **Sort indicators:** only show on the active sort column; `↑` ascending / `↓` descending; header label turns accent-purple (`#7c5cff`) on active column
- **Default sort direction:** descending for numeric columns (score, uses, updated); ascending for text columns (title, namespace, relation)
- **Row hover:** light gray/`brand-tint` background (`#f1edff` at 30% opacity)
- **Row click:** calls `onRowClick(row)` — opens the relevant Detail Drawer (per-page wiring)
- **Inline action buttons:** must call `event.stopPropagation()` to prevent triggering the row click handler (spec §2.1, §4.4)
- **Cell rendering:** plain text by default; custom `render` function for cells that display Score Pills, Namespace Dots, Relation Pills, or inline action buttons
- **Sticky header** remains visible while scrolling long tables

### 2. Pagination component (`src/dashboard_v2/src/components/table/Pagination.svelte`)

Reusable pagination footer, spec §2.1:

- **Display:** "Showing X–Y of Z" (left), prev/next chevron buttons (centered), "Page N of M" (right)
- **Default page size:** 50 rows/page (per spec §6.3)
- **Prev/next:** disabled + greyed at first/last page
- **Props:**
  - `totalRows: number` — total count
  - `page: number` — current page (1-indexed), two-way bindable
  - `pageSize: number` — rows per page (default 50), could be made configurable later
  - `onPageChange: (page: number) => void` — callback when page changes
- **Derived values:** `startRow = (page - 1) * pageSize + 1`, `endRow = min(page * pageSize, totalRows)`, `totalPages = ceil(totalRows / pageSize)`
- **Accessibility:** prev/next buttons have `aria-label="Previous page"` / `aria-label="Next page"`, page indicator uses `aria-live="polite"`

### 3. Empty state component (`src/dashboard_v2/src/components/ui/EmptyState.svelte`)

Reusable empty-state display, spec §2.10:

- **Props:**
  - `icon: string` — icon name or SVG path
  - `message: string` — primary message (e.g. "No results match this filter")
  - `description?: string` — optional secondary hint text
- **Rendering:** centered layout, icon (large, muted), bold message, muted description below
- **Used by:** DataTable when `rows.length === 0 && !loading`, and by individual pages for filter-empty states

### 4. Sorting logic (`src/dashboard_v2/src/lib/sort.ts`)

Lightweight sort utilities:

```ts
function sortRows<T>(rows: T[], column: string, direction: "asc" | "desc", isNumeric: boolean): T[];

function isNumericColumn(key: string): boolean; // heuristics for default sort direction
function toggleDirection(current: "asc" | "desc"): "asc" | "desc";
```

Sorting is client-side for the current page. Server-side sorting/pagination is handled per-page via API calls (see each page's ticket). The DataTable accepts pre-sorted rows.

### 5. Integration with DataTable

DataTable renders `<Pagination>` in its footer area. Pagination is controlled via the parent:

```svelte
<DataTable
  columns={memoryColumns}
  rows={paginatedRows}
  bind:sortColumn
  bind:sortDirection
  {onRowClick}
>
  <snippet slot="pagination">
    <Pagination {totalRows} bind:page pageSize={50} />
  </snippet>
</DataTable>
```

This keeps pagination composable rather than hardcoded inside DataTable.

## Acceptance Criteria

- [ ] DataTable renders columns as uppercase 11px headers with correct styling (muted text, `0.05em` tracking)
- [ ] Clicking a sortable column header sorts by that column; clicking again reverses direction
- [ ] Active sort column shows `↑`/`↓` indicator and purple accent header
- [ ] Row hover applies a light background tint
- [ ] Clicking a row fires `onRowClick` with the row data
- [ ] Inline action buttons inside a row do not trigger row click (verified via unit test)
- [ ] Pagination renders "Showing X–Y of Z" with correct derived values
- [ ] Prev/next chevrons are disabled + greyed at first/last page
- [ ] Changing page fires `onPageChange` callback
- [ ] Empty state renders when rows are empty (centered icon + message)
- [ ] `loading` state renders a skeleton placeholder (or spinner) while data loads
- [ ] DataTable + Pagination render correctly as independent components (unit tests)
- [ ] Custom `render` cells work (e.g. colored score pills, namespace dots)
- [ ] Sticky header stays visible during vertical scroll of long row sets
- [ ] `selectable=true` shows checkbox column (selection wiring done in LKPR-131)

## Non-goals

- No bulk-select checkbox logic (selectable column shell only — full bulk selection + action bar is LKPR-131)
- No server-side pagination wiring (each page handles its own API calls — this ticket builds the UI component only)
- No column resize/drag-to-reorder (out of scope for v2)
- No inline edit in table cells (edit happens in drawers)
- No context menus or right-click actions
- No row virtualization for 10K+ rows (defer to v3 if performance is an issue)
- No Score Pill, Namespace Dot, or Relation Pill components (those are LKPR-126 UI primitives)

## Affected Files

**New (table components):**

- `src/dashboard_v2/src/components/table/DataTable.svelte`
- `src/dashboard_v2/src/components/table/Pagination.svelte`

**New (supporting):**

- `src/dashboard_v2/src/components/ui/EmptyState.svelte`
- `src/dashboard_v2/src/lib/sort.ts`

## Dependencies

- **LKPR-122** — Tailwind design tokens (micro-size, text-muted, brand colors, etc.) must be available
- **LKPR-123** — Toast component (used later by page-level actions, not directly by DataTable itself)

## Design Ref

- **Spec:** §2.1 (Data Table), §2.10 (Empty State), §4 (cross-cutting interaction rules — row click stopPropagation, sort direction defaults), §6.3 (pagination contract — 50 rows/page, offset-based pagination)
- **Mockups:** `design/visuals/page-memories.png` (data table with sort + pagination), `design/visuals/page-links.png` (table with inline actions), `design/visuals/page-review.png` (table with checkbox column), `design/v7 - opus/Memories (standalone).html`, `design/v7 - opus/Links (standalone).html`
- **Gaps resolved:** 6.3 — 50 rows per page, offset-based pagination assumed, filter chip counts sourced server-side

## Required Updates

- **CLAUDE.md**: [ ] Add table components and sort lib to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should EmptyState be a standalone component or a slot inside DataTable? Recommend slot-based (`{#if rows.length === 0}<EmptyState ... />{/if}`) so pages can customize the empty state per context.
- Client-side vs server-side sorting for the current page? This ticket builds client-side sort of the current page. Full server-side sorting happens per-page ticket (LKPR-129, LKPR-130, etc.) when wired to real API calls.
- Pagination size: should it be configurable (e.g. 25/50/100) or fixed at 50? Start fixed at 50 per spec; add size selector if user research requests it.

## Notes

DataTable is the most-used component in the dashboard — it appears on Memories, Links, Review (2 tabs), Query results, and Sessions (implicitly). Test thoroughly with edge cases:

- Zero rows (empty state)
- Single row (no pagination needed)
- Exactly 50 rows (no overflow to page 2)
- 51 rows (page 2 has 1 row)
- Very long column values (overflow/truncation)
- Rapid column sort clicks (debounce)
- Sticky header with many rows scrolling

Build EmptyState independently first (it's also used by filter states on pages that don't use DataTable). Then build DataTable with Pagination as a slot-based footer, so pages can slot in custom pagination or omit it entirely.

## Next

**LKPR-126** — UI primitives (Score Pill, Namespace Dot, Relation Pill, Filter Chip, Segmented Control, ToggleSwitch, StatTile, HealthRing, HeatmapGrid)
