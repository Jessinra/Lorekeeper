---
id: LKPR-131
title: Review Inbox page — Suggestions/Stale tabs, bulk-select, inline triage, RelationshipDrawer drill-down
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 296
---

# [LKPR-131] Review Inbox page — Suggestions/Stale tabs, bulk-select, inline triage, RelationshipDrawer drill-down

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The current v1 Suggestions tab (at `suggestions.js`) is a single flat table with accept/reject inline buttons and pagination — but it has no Stale tab, no segmented control, no bulk-select action bar, and no RelationshipDrawer for exploring a suggestion's full context before acting. The v1 UI requires users to batch-operate on suggestions without seeing the memory details inline, and stale memories have no dedicated review surface at all.

The v7 design spec (§3.5) defines a **Review Inbox** as a two-tab page with a SegmentedControl (Suggestions/Stale), each tab being a bulk-selectable DataTable with inline action buttons and a RelationshipDrawer on row click.

## Solution

Build a **Review Inbox page** at `src/dashboard_v2/src/routes/review.svelte` with:

### Layout (spec §3.5)

```
┌──────────────────────────────────────────────────────────────────┐
│  Review Inbox                                                     │
│  ┌───────────────────────────────┐                                │
│  │ [Suggestions ● 5,284] [Stale 37] │  Sort: [Score ▼]  [↺]     │
│  └───────────────────────────────┘                                │
│                                                                   │
│  ┌─┬───────────┬──────────┬───────────┬───────┬───────────────┐  │
│  │☐│ SOURCE    │ RELATION │ TARGET    │ SCORE │               │  │
│  ├─┼───────────┼──────────┼───────────┼───────┼───────────────┤  │
│  │☐│ Memory A  │references│ Memory B  │  0.92 │ [✓] [✗]      │  │
│  │☐│ Memory C  │supersedes│ Memory D  │  0.87 │ [✓] [✗]      │  │
│  └─┴───────────┴──────────┴───────────┴───────┴───────────────┘  │
│  ──────────────────────────────────────────────────────────────── │
│  Showing 1–50 of 5,284    < Page 1 of 106 >                       │
└──────────────────────────────────────────────────────────────────┘
```

### SegmentedControl (spec §2.10)

- Two-tab pill group: **Suggestions** (with live pending count badge) and **Stale** (with live stale count badge)
- White active tab indicator, switches the table content below
- Counts fetched from `GET /api/suggestions/count` and `GET /api/memories/stale/count`

### Suggestions tab

**DataTable** (spec §2.1) with bulk-select column (spec §2.6):

| Column       | Type         | Notes                                                           |
| ------------ | ------------ | --------------------------------------------------------------- |
| ☐ (checkbox) | select       | Header checkbox toggles all visible rows                        |
| Source       | text         | Clickable title → opens memory detail                           |
| Relation     | RelationPill | Colored per spec §2.5                                           |
| Target       | text         | Clickable title → opens memory detail                           |
| Score        | ScorePill    | 0–1.0 score, colored per spec §2.3                              |
| Actions      | [✓] [✗]      | Accept (green) / Reject (red) inline buttons, immediate + toast |

- Row click → opens **RelationshipDrawer** (LKPR-128) with the same Accept/Reject actions in the footer.
- Inline accept/reject buttons fire `stopPropagation()` so they don't trigger the drawer.
- Sort dropdown: Score (desc/asc), Newest first.
- **Bulk action bar** (spec §2.6): when ≥1 row is checked, header caption ("5,284 pending suggestions") is replaced by "N selected" + Accept selected / Reject selected buttons.

### Stale tab

**DataTable** with bulk-select column:

| Column       | Type         | Notes                                                    |
| ------------ | ------------ | -------------------------------------------------------- |
| ☐ (checkbox) | select       | Header checkbox toggles all visible rows                 |
| Memory       | text         | Memory title, clickable → opens MemoryDetailDrawer       |
| NS           | NamespaceDot | Colored per spec §2.4                                    |
| Score        | ScorePill    | 0–10 score, colored per spec §2.3                        |
| Last used    | text         | "Xd ago" relative time                                   |
| Actions      | [↺] [✗]      | Refresh (time icon) / Delete (trash icon) inline buttons |

- Row click → opens **MemoryDetailDrawer** (LKPR-127) with Refresh/Delete actions in the footer.
- Inline Refresh marks the memory as used today via `POST /api/memories/:id/refresh` → toast.
- Inline Delete fires immediately with a toast (per spec §4.1, stale-delete is lightweight, not confirm-gated — see open question §6.6).
- **Bulk action bar**: when ≥1 row is checked, "N selected" + Refresh selected / Delete selected buttons.

### Empty states

- Suggestions tab empty: "No pending suggestions — sweep engine is running and up to date."
- Stale tab empty: "No stale memories — all memories are actively used."

### API dependencies

- `GET /api/suggestions` — exists at `/api/suggestions` with pagination, sort, `memory_id` filter. Already supports `limit`, `offset`, `sort_by`, `sort_dir`. The v2 mount needs to keep this contract.
- `GET /api/suggestions/count` — exists at `/api/suggestions/count`.
- `POST /api/suggestions/batch` — exists at `/api/suggestions/batch`. Accepts `{ suggestion_ids: string[], action: "accept" | "reject" }`.
- `POST /api/memories/:id/refresh` — **needs creation** (per dashboard-v2-epic.md API table). Marks a memory as "used today" by bumping `usage_count` and `updated_at`.
- `GET /api/memories/stale` — needs creation (or v2 mount of existing). Returns memories with low usage count and old `updated_at`. Accepts `sort`, `page`, `page_size`.
- `GET /api/memories/stale/count` — needs creation. Returns count of stale memories.

## Acceptance Criteria

- [ ] SegmentedControl shows Suggestions and Stale tabs with live count badges
- [ ] Suggestions tab renders DataTable with Source, RelationPill, Target, ScorePill, inline Accept/Reject
- [ ] Stale tab renders DataTable with Memory, NamespaceDot, ScorePill, Last used, inline Refresh/Delete
- [ ] Row click on Suggestions opens RelationshipDrawer with Accept/Reject actions
- [ ] Row click on Stale opens MemoryDetailDrawer with Refresh/Delete actions
- [ ] Inline Accept/Reject fires immediately → toast confirmation → row removed from list without page reload
- [ ] Inline Refresh fires POST → toast → row updated
- [ ] Inline Delete fires immediately → toast → row removed
- [ ] Bulk-select checkbox toggles all visible rows
- [ ] Bulk action bar replaces header caption when ≥1 row selected
- [ ] Bulk Accept/Reject/Refresh/Delete processes all checked rows → toast with count → selection cleared
- [ ] Sort dropdown changes the table sort order
- [ ] Pagination footer shows range, prev/next buttons
- [ ] Empty state renders for each tab when no items
- [ ] All inline action buttons call `stopPropagation()` to prevent drawer-trigger

## Non-goals

- No Y/N keyboard triage shortcuts (see spec §6.8 — out of scope for v2)
- No graph view from Review (use Links page)
- No nav badge integration (see spec §6.2 — pending product decision on what the badge counts)

## Affected Files

**New:**

- `src/dashboard_v2/src/routes/review.svelte` — Review page: SegmentedControl, two DataTable tabs, bulk action bar, empty states

**Modified:**

- `src/dashboard_v2/src/lib/api.ts` — add `fetchSuggestions()`, `batchAction()`, `fetchStaleMemories()`, `refreshMemory()`, `fetchSuggestionCount()`, `fetchStaleCount()`
- Backend: `src/lorekeeper/dashboard/routes/memories.py` — add `POST /api/memories/:id/refresh` endpoint
- Backend: `src/lorekeeper/dashboard/routes/memories.py` — add `GET /api/memories/stale` and `GET /api/memories/stale/count` endpoints

## Dependencies

- **LKPR-128** (RelationshipDrawer) — required for suggestion row-click drill-down
- **LKPR-127** (MemoryDetailDrawer) — required for stale row-click drill-down
- **LKPR-126** (UI primitives) — ScorePill, NamespaceDot, RelationPill, FilterChip, SegmentedControl
- **LKPR-125** (DataTable + pagination) — the core table component with sortable columns
- **LKPR-122** (Scaffold, shell, design tokens) — app shell and nav rail

## Required Updates

- **CLAUDE.md**: [ ] Add `routes/review.svelte` to project map under dashboard v2
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] Update dashboard-v2-epic.md progress tracker to mark LKPR-131 as done

## Notes

The v1 `suggestions.js` has a fully working paginated table with batch operations — this ticket is a full rewrite in Svelte 5, not an incremental patch. Use the v1 API surface as the data contract reference.

The `POST /api/memories/:id/refresh` endpoint is a new addition. It should bump `usage_count += 1` and update `updated_at` to now. Existing v1 Memories tab doesn't need this endpoint, only the Review Stale tab does.

Spec §6.6 flags an inconsistency: stale-delete on the Stale tab fires immediately with no confirm dialog, while every other destructive action in the app confirms first. The ticket follows the spec's house rule (§4.1) that stale-delete is lightweight/reversible and doesn't confirm. If product decides otherwise, add a ConfirmDialog before the delete action.

## Next

**LKPR-132** — Links table view (data table + relation pill + Relationship Drawer)
