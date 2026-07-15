---
id: LKPR-132
title: Links table view — sortable table, RelationPill colors, RelationshipDrawer, delete with ConfirmDialog
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 297
---

# [LKPR-132] Links table view — sortable table, RelationPill colors, RelationshipDrawer, delete with ConfirmDialog

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The current v1 Links tab (at `links.js`) renders a flat table with Source, Relation badge, Target, Reason, Score, Uses, and a delete button. It uses inline `confirm()` for deletes, has no RelationPill color coding per spec §2.5, no RelationType legend/filter chips, no Graph/Links SegmentedControl (Graph tab is a placeholder), and no RelationshipDrawer on row click. The delete action uses a browser `confirm()` dialog instead of the app's ConfirmDialog component.

The v7 design spec (§3.3, table view only) defines a Links page with a relation-type legend/filter row, a Graph/Links SegmentedControl (Links tab active, Graph tab disabled placeholder), and a polished DataTable that opens the RelationshipDrawer on row click.

## Solution

Build the **Links table view** at `src/dashboard_v2/src/routes/links.svelte` with:

### Layout (spec §3.3, table view only)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Links                                                                   │
│                                                                          │
│  [references] [contradicts] [supersedes] [duplicate_of] [used_by] [All]  │
│                                                                          │
│  [Graph (disabled)] [Links ●]                                            │
│                                                                          │
│  ┌───────────┬──────────┬───────────┬──────────┬───────┬──────┬──────┐  │
│  │ SOURCE    │ RELATION │ TARGET    │ REASON   │ SCORE │ USES │      │  │
│  ├───────────┼──────────┼───────────┼──────────┼───────┼──────┼──────┤  │
│  │ Memory A  │references│ Memory B  │ because… │  7.2  │   12 │  🗑  │  │
│  │ Memory C  │supersedes│ Memory D  │ because… │  9.1  │    8 │  🗑  │  │
│  └───────────┴──────────┴───────────┴──────────┴───────┴──────┴──────┘  │
│  ──────────────────────────────────────────────────────────────────────── │
│  Showing 1–50 of 142    < Page 1 of 3 >                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

1. **RelationType legend/filter chips** — a row of colored pill buttons, one per relation type, using the colors from spec §2.5:

   - `references` → `#d97706` (amber)
   - `contradicts` → `#dc2626` (red)
   - `supersedes` → `#7c5cff` (purple)
   - `duplicate_of` → `#92400e` (brown)
   - `used_by` → `#16a34a` (green)
   - Plus an `All` chip that clears the filter.

   Each chip toggles between active (filled color background) and inactive (outline). Active chip filters the table to only that relation type. Multiple chips can be active simultaneously.

2. **SegmentedControl** — Graph/Links toggle (spec §2.10):

   - **Links tab** (active): shows the DataTable.
   - **Graph tab** (disabled): renders a disabled/placeholder state with text "Graph view — coming in a future release" (blocked per spec §6.4).

3. **DataTable** (spec §2.1) with sortable columns:

   | Column   | Type             | Sort direction (first click) | Notes                               |
   | -------- | ---------------- | ---------------------------- | ----------------------------------- |
   | Source   | text (clickable) | Ascending                    | Opens memory detail on click        |
   | Relation | RelationPill     | —                            | Colored per spec §2.5, not sortable |
   | Target   | text (clickable) | Ascending                    | Opens memory detail on click        |
   | Reason   | text (truncated) | —                            | Tooltip on hover for full text      |
   | Score    | ScorePill        | Descending                   | 0–10 score, colored per spec §2.3   |
   | Uses     | number           | Descending                   | Usage count                         |
   | (delete) | icon button      | —                            | Trash icon, opens ConfirmDialog     |

4. **Row click** → opens **RelationshipDrawer** (spec §2.2-B, LKPR-128) showing:

   - Source memory card (role label, title, namespace + score chips, description, content)
   - RelationPill with directional arrow
   - Target memory card
   - Stat row (score, uses, created date)
   - Footer: single "Delete this link" button (destructive, opens ConfirmDialog)

5. **Delete icon** (trailing column) → opens **ConfirmDialog** (spec §2.7):

   - Icon swatch: red (destructive)
   - Title: "Delete this link?"
   - Body: "This will remove the relationship between Source and Target. The memories themselves will not be affected."
   - Buttons: Cancel (secondary) / Delete (destructive, red)
   - On confirm: `DELETE /api/links/:id` → toast "Link deleted" → row removed from table.

6. **Pagination footer** — "Showing X–Y of Z", 50 rows/page, prev/next chevrons.

7. **Empty state** — "No links match this filter" when filter yields no results. "No links yet — links appear when the sweep engine finds relationships between memories" when the table is empty with no filter.

### API dependencies

- `GET /api/links?relation=&sort=&page=&page_size=` — existing `/api/links` returns all links. The v2 mount needs filter (by relation type), sort, and pagination support. Existing endpoint already supports `include_deleted` param.
- `DELETE /api/links/:id` — exists at `/api/links/:id`, returns `{"ok": true}`.

## Acceptance Criteria

- [ ] RelationType legend/filter chips render with correct colors per spec §2.5
- [ ] Clicking a relation chip filters the table to that relation type (multiple chips can be active)
- [ ] Clicking "All" clears all relation filters
- [ ] SegmentedControl renders Graph (disabled) and Links (active) tabs
- [ ] Graph tab shows placeholder text about future release
- [ ] DataTable renders Source, RelationPill, Target, Reason, ScorePill, Uses, delete icon
- [ ] Columns are sortable: Source (asc), Target (asc), Score (desc), Uses (desc)
- [ ] RelationPill colors match spec §2.5 exactly
- [ ] ScorePill colors match spec §2.3 boundaries
- [ ] Row click opens RelationshipDrawer with source/target cards and delete action
- [ ] Delete icon opens ConfirmDialog (not browser `confirm()`)
- [ ] ConfirmDialog confirm → `DELETE` request → toast → row removed
- [ ] ConfirmDialog cancel → no action
- [ ] Pagination renders correctly with prev/next and range label
- [ ] Empty state renders when no links match filter
- [ ] Empty state renders when there are no links at all

## Non-goals

- No Graph view implementation (blocked per spec §6.4 — placeholder only)
- No link creation UI (links are created via sweep engine or suggestion acceptance)
- No link edit UI (links are immutable once created — delete and re-create)
- No inline memory detail on link source/target names (that's the RelationshipDrawer's job)

## Affected Files

**New:**

- `src/dashboard_v2/src/routes/links.svelte` — Links page: RelationType chips, SegmentedControl, DataTable, empty states

**Modified:**

- `src/dashboard_v2/src/lib/api.ts` — add `fetchLinks()`, `deleteLink()` methods
- Backend: `src/lorekeeper/dashboard/routes/links.py` — enhance `/api/links` to support `relation`, `sort`, `page`, `page_size` query params

## Dependencies

- **LKPR-128** (RelationshipDrawer) — required for row-click drill-down
- **LKPR-126** (UI primitives) — RelationPill, ScorePill, NamespaceDot, FilterChip, SegmentedControl
- **LKPR-125** (DataTable + pagination) — the core table component with sortable columns
- **LKPR-123** (ConfirmDialog) — required for delete confirmation
- **LKPR-122** (Scaffold, shell, design tokens) — app shell and nav rail

## Required Updates

- **CLAUDE.md**: [ ] Add `routes/links.svelte` to project map under dashboard v2
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] Update dashboard-v2-epic.md progress tracker to mark LKPR-132 as done

## Notes

The v1 `links.js` has a working `setLinkRelationFilter()` and `deleteLinkFromTab()` — use these as reference for the API contract. The v2 rewrite must use the ConfirmDialog component instead of browser `confirm()`.

The RelationPill color map must be defined as a shared constant (in `utils.ts` or the RelationPill component itself) so it's consistent across this page, Review, and the RelationshipDrawer. Do not duplicate the map.

The Graph view is category-blocked per §6.4 — the SegmentedControl's Graph tab should render a disabled state with a subtle message. The graph UI will be built in LKPR-138 when the design decision is resolved.

## Next

**LKPR-133** — Query page (split layout, result list, signal inspector)
