# LKPR-125 — Data Table + Pagination Implementation Plan

**Status:** 🟢 Plan ready | **Branch:** `feat/LKPR-125-data-table-pagination` | **PR:** TBD

## Summary

Build reusable Svelte 5 components for the dashboard v2: `DataTable`, `Pagination`, `EmptyState`, and `sort.ts` utilities. These are the foundation for every page that displays tabular data (Memories, Links, Review, Sessions, Query).

## Files to Create

| File                                                       | Purpose                                                     |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `src/dashboard_v2/src/lib/sort.ts`                         | Sort utilities (sortRows, isNumericColumn, toggleDirection) |
| `src/dashboard_v2/src/lib/sort.test.ts`                    | Unit tests for sort utilities                               |
| `src/dashboard_v2/src/components/table/Pagination.svelte`  | Pagination footer component                                 |
| `src/dashboard_v2/src/components/table/Pagination.test.ts` | Unit tests for Pagination                                   |
| `src/dashboard_v2/src/components/table/DataTable.svelte`   | Generic data table component                                |
| `src/dashboard_v2/src/components/table/DataTable.test.ts`  | Unit tests for DataTable                                    |
| `src/dashboard_v2/src/components/ui/EmptyState.svelte`     | Reusable empty state component                              |
| `src/dashboard_v2/src/components/ui/EmptyState.test.ts`    | Unit tests for EmptyState                                   |

## Implementation Order

### 1. `sort.ts` — Sort utilities (no deps)

- `sortRows<T>(rows, column, direction, isNumeric): T[]` — stable sort by column key
- `isNumericColumn(key): boolean` — heuristic: `score`, `uses`, `updated`, `confidence`, `count` → true
- `toggleDirection(current): 'asc' | 'desc'` — simple toggle
- No external deps, pure TypeScript

### 2. `EmptyState.svelte` — UI component (no deps)

- Props: `icon: string`, `message: string`, `description?: string`
- Centered layout, large muted icon, bold message, optional description
- Uses existing CSS tokens (surface background, text-muted, text-faint)

### 3. `Pagination.svelte` — UI component (no deps)

- Props: `totalRows: number`, `page: number` (bindable, 1-indexed), `pageSize: number` (default 50), `onPageChange: (page: number) => void`
- Derived: startRow, endRow, totalPages
- Display: "Showing X–Y of Z" (left), prev/next chevrons (center), "Page N of M" (right)
- Prev/next disabled at boundaries
- Accessibility: `aria-label` on buttons, `aria-live="polite"` on page indicator

### 4. `DataTable.svelte` — Main component (depends on EmptyState, Pagination, sort)

- Column interface: `Column<T>` with `key`, `label`, `sortable?`, `sortKey?`, `width?`, `align?`, `render?`
- Props: `columns`, `rows`, `sortColumn` (bindable), `sortDirection` (bindable), `onRowClick`, `selectable?`, `selectedRows?`, `emptyMessage?`, `loading?`
- Sticky header with uppercase 11px muted labels
- Sort indicators on active column, purple accent
- Row hover tint, row click → `onRowClick`
- `stopPropagation()` on inline action buttons
- Pagination slot for composable footer
- Empty state via EmptyState when rows empty
- Loading skeleton state

## Design Decisions

1. **EmptyState as slot-based pattern** — DataTable renders `{#if rows.length === 0 && !loading}<EmptyState ... />{/if}` inside the component, but also exposes an `emptyMessage` prop. Pages can fully customize by not using DataTable's empty state and doing their own handling.

2. **Pagination as slot** — DataTable has a `{#snippet pagination()}...{/snippet}` slot so pages can customize or omit pagination. The default slot includes `<Pagination>`.

3. **Client-side sort only** — sortRows sorts the current page array. Server-side pagination is per-page responsibility (LKPR-129, LKPR-130, etc.).

4. **Testing approach** — vitest + jsdom + @testing-library/svelte. Pure TS tests for sort.ts, component tests for Svelte components.

## Edge Cases to Cover

- Empty rows array → EmptyState
- Single row → no pagination needed
- 51 rows → page 2 has 1 row
- Loading state → skeleton/spinner
- Rapid sort clicks → stable sort, no debounce needed (client-side)
- Sticky header with scroll
- `selectable=true` → checkbox column rendered (no select logic — LKPR-131)

## Verification

- `cd src/dashboard_v2 && npm run test` — all tests pass
- Visual check: `npm run dev`, navigate to a page that mounts DataTable
