# Dashboard V2 — Master Epic & Progress Tracker

**Status:** 🟢 Planning | **Branch:** `dashboard-revamp` | **Target:** `src/dashboard_v2/`

## Overview

Complete revamp of the Lorekeeper dashboard — Svelte 5 + Tailwind CSS v4, rebuilding the entire UI from scratch at `src/dashboard_v2/`. New design based on `design/Lorekeeper-Dashboard-v7-Design-Spec.md` and mockups in `design/v7 - opus/*.html` and `design/visuals/*.png`.

**Key principles:**

- Small, independently verifiable tickets — each ticket produces a working artifact
- Reusable Svelte components built alongside their first consumer page
- Every page must match the mockup pixel-for-pixel
- Design tokens enforced via Tailwind config (see spec §8)
- Testing required — unit tests for components, E2E for pages
- Each ticket includes a "Next" field — sequential build order
- Existing v1 dashboard (`src/lorekeeper/dashboard/`) remains untouched

## Build Sequence

```
Phase 1: Foundation (tickets 1-3)
  └── Scaffold + shell + tokens → Toast + Dialog → Command Palette

Phase 2: Shared components (tickets 4-7)
  └── Data Table → UI Primitives → Memory Drawer → Relationship Drawer

Phase 3: Primary pages (tickets 8-11)
  └── Memories → Sessions → Review → Links Table

Phase 4: Secondary pages (tickets 12-16)
  └── Query → Home → Metrics → Settings → E2E Tests

Phase 5: Graph (blocked)
  └── Graph Canvas (awaiting design decision on §6.4)
```

## Progress Tracker

| Ticket       | Title                          | Status     | PR  | Notes                                          |
| ------------ | ------------------------------ | ---------- | --- | ---------------------------------------------- |
| **LKPR-122** | Scaffold, shell, design tokens | ⬜ Pending | —   | Foundation — everything depends on this        |
| **LKPR-123** | Toast + Confirm Dialog         | ⬜ Pending | —   | Reusable overlay components                    |
| **LKPR-124** | Command Palette                | ⬜ Pending | —   | Global ⌘K overlay                              |
| **LKPR-125** | Data Table + pagination        | ⬜ Pending | —   | Sortable table, pagination, empty state        |
| **LKPR-126** | UI primitives                  | ⬜ Pending | —   | Score Pill, Namespace Dot, Relation Pill, etc. |
| **LKPR-127** | Memory Detail Drawer           | ⬜ Pending | —   | View + edit mode, danger zone                  |
| **LKPR-128** | Relationship Drawer            | ⬜ Pending | —   | Read-only memory cards + relation pill         |
| **LKPR-129** | Memories page                  | ⬜ Pending | —   | Wires data table + filters + drawer + search   |
| **LKPR-130** | Sessions page                  | ⬜ Pending | —   | Timeline, session drawer, stacked drawer       |
| **LKPR-131** | Review Inbox                   | ⬜ Pending | —   | Two-tab, bulk select, inline actions           |
| **LKPR-132** | Links table view               | ⬜ Pending | —   | Table + relation pill + Relationship Drawer    |
| **LKPR-133** | Query page                     | ⬜ Pending | —   | Split layout, result list, signal inspector    |
| **LKPR-134** | Home page                      | ⬜ Pending | —   | Health ring, stat tiles, activity feed         |
| **LKPR-135** | Metrics page                   | ⬜ Pending | —   | Heatmap grid + per-tool mini heatmaps          |
| **LKPR-136** | Settings page                  | ⬜ Pending | —   | 6 form sections, unsaved indicator             |
| **LKPR-137** | E2E + visual regression        | ⬜ Pending | —   | Playwright tests, CI integration               |
| **LKPR-138** | Graph canvas                   | ⬜ Blocked | —   | Awaiting design decision on §6.4               |

## Directory Structure

```
src/dashboard_v2/
├── app.html                    # SvelteKit HTML shell
├── src/
│   ├── routes/                 # Page routes (hash-based SPA)
│   │   ├── home.svelte
│   │   ├── memories.svelte
│   │   ├── sessions.svelte
│   │   ├── review.svelte
│   │   ├── links.svelte
│   │   ├── query.svelte
│   │   ├── metrics.svelte
│   │   └── settings.svelte
│   ├── components/             # Reusable components
│   │   ├── shell/
│   │   │   ├── NavRail.svelte
│   │   │   ├── TopBar.svelte
│   │   │   └── AppShell.svelte
│   │   ├── table/
│   │   │   ├── DataTable.svelte
│   │   │   └── Pagination.svelte
│   │   ├── drawers/
│   │   │   ├── MemoryDetailDrawer.svelte
│   │   │   ├── RelationshipDrawer.svelte
│   │   │   └── SessionDrawer.svelte
│   │   ├── overlays/
│   │   │   ├── ConfirmDialog.svelte
│   │   │   ├── Toast.svelte
│   │   │   └── CommandPalette.svelte
│   │   ├── ui/
│   │   │   ├── ScorePill.svelte
│   │   │   ├── NamespaceDot.svelte
│   │   │   ├── RelationPill.svelte
│   │   │   ├── FilterChip.svelte
│   │   │   ├── SegmentedControl.svelte
│   │   │   ├── ToggleSwitch.svelte
│   │   │   ├── StatTile.svelte
│   │   │   ├── HealthRing.svelte
│   │   │   ├── HeatmapGrid.svelte
│   │   │   └── EmptyState.svelte
│   │   └── graph/
│   │       └── GraphView.svelte
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── router.ts           # Hash-based SPA router
│   │   ├── toast.ts            # Toast store
│   │   └── utils.ts            # Formatters, helpers
│   └── app.css                 # Tailwind base + global styles
├── tailwind.config.ts          # Design tokens (spec §8)
├── vite.config.ts
├── svelte.config.js
├── package.json
└── tsconfig.json
```

## Design Tokens (Tailwind Config)

From spec §8 — all values must be exact:

| Token            | Value                                              | Usage                                       |
| ---------------- | -------------------------------------------------- | ------------------------------------------- |
| `background`     | `#f9f9fb`                                          | Page canvas                                 |
| `text-primary`   | `#1a1a2e`                                          | Headings                                    |
| `text-body`      | `#3f3f52`                                          | Body copy                                   |
| `text-muted`     | `#6b7280`                                          | Secondary labels                            |
| `text-faint`     | `#9ca3af`                                          | Placeholders                                |
| `border`         | `#e6e6ee`                                          | Borders                                     |
| `divider`        | `#eeeef3`                                          | Dividers                                    |
| `brand`          | `#7c5cff`                                          | Primary actions                             |
| `brand-hover`    | `#6a46f5`                                          | Active link/hover                           |
| `brand-tint`     | `#f1edff`                                          | Active bg                                   |
| `success-bg`     | `#ecfdf3`                                          | Green pills                                 |
| `success-text`   | `#16a34a`                                          | Green text                                  |
| `warning-bg`     | `#fef6e7`                                          | Amber pills                                 |
| `warning-text`   | `#d97706`                                          | Amber text                                  |
| `danger-bg`      | `#fef2f2`                                          | Red pills                                   |
| `danger-text`    | `#dc2626`                                          | Red text                                    |
| `card-radius`    | `14px`                                             | Cards                                       |
| `control-radius` | `9px`                                              | Buttons, inputs                             |
| `pill-radius`    | `999px`                                            | Chips, badges                               |
| `font-family`    | `-apple-system, "Segoe UI", system-ui, sans-serif` | All text                                    |
| `body-size`      | `13px`                                             | Table/body text                             |
| `micro-size`     | `11px`                                             | Column headers (uppercase, 0.05em tracking) |

## Layout Constants

- Nav rail: `76px` wide, fixed left, full viewport height
- Top bar: `60px` tall, sticky, `z-index` above page content
- Page body: `margin-left: 76px` to clear nav rail
- Drawer: `440-460px` wide, capped at `92vw`
- Command Palette: `640px` wide centered modal
- Confirm Dialog: `~400px` wide centered card
- Toast: bottom-center, auto-dismiss `1.7-1.9s`

## API Dependencies

The v2 dashboard relies on the existing v1 API routes under `/api/`. Some endpoints need enhancement (pagination, filter params). The v2 FastAPI mount adds a `/v2/` prefix, proxying to the same underlying stores.

| Endpoint                                | Status                     | Needed for           |
| --------------------------------------- | -------------------------- | -------------------- |
| `GET /api/v2/memories`                  | Needs pagination + filters | Memories page        |
| `GET /api/v2/memories/:id`              | Exists                     | Memory drawer        |
| `PATCH /api/v2/memories/:id`            | Exists                     | Memory drawer edit   |
| `DELETE /api/v2/memories/:id`           | Exists                     | Memory drawer delete |
| `POST /api/v2/memories/:id/soft-delete` | Needs creation             | Memory drawer        |
| `POST /api/v2/memories/:id/refresh`     | Needs creation             | Review stale         |
| `GET /api/v2/links`                     | Needs pagination + filters | Links table          |
| `DELETE /api/v2/links/:id`              | Exists                     | Links table          |
| `GET /api/v2/suggestions`               | Exists (paginated)         | Review               |
| `POST /api/v2/suggestions/batch`        | Exists                     | Review               |
| `GET /api/v2/sessions`                  | Needs task-type filter     | Sessions             |
| `GET /api/v2/sessions/:id`              | Exists                     | Sessions drawer      |
| `POST /api/v2/query/debug`              | Needs creation             | Query page           |
| `GET /api/v2/metrics/tool-calls`        | Needs 7d hourly agg        | Metrics              |
| `GET /api/v2/health`                    | Needs creation             | Home page            |
| `GET /api/v2/settings`                  | Exists                     | Settings             |
| `PATCH /api/v2/settings`                | Exists                     | Settings             |
| `POST /api/v2/export`                   | Exists                     | Settings             |
| `POST /api/v2/import/preview`           | Exists                     | Settings             |
| `POST /api/v2/import/confirm`           | Exists                     | Settings             |
| `POST /api/v2/sweep/run`                | Exists                     | Settings             |

## Pending Design Decisions

These are tracked in the design spec (§6) and must be resolved before the affected tickets can be completed:

| Gap                               | Affects  | Status                                   |
| --------------------------------- | -------- | ---------------------------------------- |
| 6.1 Nav rail inconsistencies      | LKPR-122 | Resolved in spec (7-item list)           |
| 6.2 Review nav badge semantics    | LKPR-131 | Needs product decision                   |
| 6.3 Pagination contract           | LKPR-129 | Needs backend pagination                 |
| 6.4 Graph scalability             | LKPR-138 | BLOCKED — needs design decision          |
| 6.5 Missing "New memory" composer | LKPR-129 | Stub as toast for now                    |
| 6.6 Stale-delete confirm          | LKPR-131 | Follow spec §4.1 (require confirmation)  |
| 6.7 Score threshold inconsistency | All      | Standardize on ≥5 amber boundary         |
| 6.8 Y/N keyboard triage           | LKPR-131 | Out of scope for v2                      |
| 6.9 Settings persistence          | LKPR-136 | Uses persistent config API (exists)      |
| 6.10 Weight validation            | LKPR-136 | Soft warning (flag, don't block save)    |
| 6.11 Command Palette backend      | LKPR-124 | Stub with local list initially           |
| 6.12 Timezone handling            | LKPR-135 | Use server timezone (existing API)       |
| 6.13 Digest window                | LKPR-134 | Rolling 24h (assumption)                 |
| 6.14 Activity feed click-through  | LKPR-134 | Navigate to relevant page per event type |
