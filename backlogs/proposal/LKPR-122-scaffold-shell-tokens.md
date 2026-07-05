---
id: LKPR-122
title: Scaffold, shell, design tokens
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 287
---

# [LKPR-122] Scaffold, shell, design tokens

## Problem

Phase 1 of the dashboard v2 revamp has no foundation to build on. There is no SvelteKit project at `src/dashboard_v2/`, no shared layout shell, no design tokens configured. Every subsequent ticket (LKPR-123 through LKPR-137) depends on this base being in place — the nav rail, top bar, page body skeleton, and a Tailwind config that matches the design spec exactly.

Without this ticket, every component and page would be built in isolation with no shared layout, no consistent spacing/sizing, and no way to verify against the mockups pixel-for-pixel.

## Solution

Scaffold a Svelte 5 + Tailwind CSS v4 + TypeScript project at `src/dashboard_v2/` with:

### 1. Project scaffold

- `package.json` with Svelte 5, SvelteKit, Tailwind v4, TypeScript dependencies
- `svelte.config.js` — adapter-static (SPA mode, hash-based routing)
- `vite.config.ts` — SvelteKit Vite config
- `tsconfig.json` — strict TypeScript preset
- `app.html` — SvelteKit HTML shell with `<div id="app">` mount point

### 2. Design tokens (Tailwind config)

Exact values from spec §8 — every color, radius, font size, and spacing constant must match pixel-for-pixel:

| Token            | Value     | Usage                                       |
| ---------------- | --------- | ------------------------------------------- |
| `background`     | `#f9f9fb` | Page canvas                                 |
| `text-primary`   | `#1a1a2e` | Headings                                    |
| `text-body`      | `#3f3f52` | Body copy                                   |
| `text-muted`     | `#6b7280` | Secondary labels                            |
| `text-faint`     | `#9ca3af` | Placeholders                                |
| `border`         | `#e6e6ee` | Borders                                     |
| `divider`        | `#eeeef3` | Dividers                                    |
| `brand`          | `#7c5cff` | Primary actions                             |
| `brand-hover`    | `#6a46f5` | Active link/hover                           |
| `brand-tint`     | `#f1edff` | Active bg                                   |
| `success-bg`     | `#ecfdf3` | Green pills                                 |
| `success-text`   | `#16a34a` | Green text                                  |
| `warning-bg`     | `#fef6e7` | Amber pills                                 |
| `warning-text`   | `#d97706` | Amber text                                  |
| `danger-bg`      | `#fef2f2` | Red pills                                   |
| `danger-text`    | `#dc2626` | Red text                                    |
| `card-radius`    | `14px`    | Cards                                       |
| `control-radius` | `9px`     | Buttons, inputs                             |
| `pill-radius`    | `999px`   | Chips, badges                               |
| `body-size`      | `13px`    | Table/body text                             |
| `micro-size`     | `11px`    | Column headers (uppercase, 0.05em tracking) |

Font family: `-apple-system, "Segoe UI", system-ui, sans-serif`.

### 3. App shell components

Three components in `src/dashboard_v2/src/components/shell/`:

- **`AppShell.svelte`** — layout skeleton: fixed 76px nav rail (left), 60px sticky top bar, page `<slot>` with `margin-left: 76px`. Wraps all page routes.
- **`NavRail.svelte`** — 7-item nav list (Home, Memories, Links, Query, Review, Sessions, Metrics) + Settings pinned to bottom + brand mark. Active item: purple bg/icon/bold label. See spec §1.2 and gap 6.1 (resolved: use the canonical 7-item list).
- **`TopBar.svelte`** — breadcrumb ("Lorekeeper / {page name}") left, Command Palette trigger (styled search input with `⌘K` hint) right. See spec §1.3.

### 4. Layout constants

- Nav rail: `76px` wide, fixed left, full viewport height, white, right border
- Top bar: `60px` tall, sticky, white, bottom border, `z-index` above page content
- Page body: `margin-left: 76px` to clear nav rail
- Command Palette: `640px` wide centered modal
- Confirm Dialog: `~400px` wide centered card
- Toast: bottom-center, auto-dismiss `1.7–1.9s`
- Drawer: `440–460px` wide, capped at `92vw`

### 5. Global styles

- `app.css` — Tailwind base imports + global styles: `@import "tailwindcss"`, CSS custom properties for tokens, scrollbar styling, focus ring (purple brand color), body font + size defaults.

## Acceptance Criteria

- [ ] `src/dashboard_v2/` exists with SvelteKit project scaffold, builds with `npm run build`
- [ ] `tailwind.config.ts` defines all design tokens from spec §8 — exact hex values, radii, font sizes
- [ ] `AppShell.svelte` renders nav rail (76px) + top bar (60px) + page slot with correct z-index layering
- [ ] `NavRail.svelte` renders the canonical 7-item list (Home, Memories, Links, Query, Review, Sessions, Metrics) + Settings, with active state styling (purple bg/tint, bold label)
- [ ] `TopBar.svelte` renders breadcrumb + ⌘K search trigger button
- [ ] `app.css` applies base body font, size (13px), and background (#f9f9fb)
- [ ] `npm run dev` starts without errors, nav shell is visible at `/`
- [ ] Page content area clears the nav rail correctly (76px left margin)
- [ ] Layout constants match spec: nav rail 76px, top bar 60px, drawer 440–460px, command palette 640px, confirm dialog ~400px

## Non-goals

- No page content beyond the shell (stub each route as a simple heading)
- No Command Palette logic — just the trigger button in the top bar (actual palette is LKPR-124)
- No toast store or dialog state management (those arrive with LKPR-123)
- No hash-based router implementation (stub routing — full router is LKPR-126 or earlier if needed)
- No API client (arrives with LKPR-126 lib/)

## Affected Files

**New:**

- `src/dashboard_v2/package.json`
- `src/dashboard_v2/svelte.config.js`
- `src/dashboard_v2/vite.config.ts`
- `src/dashboard_v2/tsconfig.json`
- `src/dashboard_v2/tailwind.config.ts`
- `src/dashboard_v2/app.html`
- `src/dashboard_v2/src/app.css`
- `src/dashboard_v2/src/components/shell/AppShell.svelte`
- `src/dashboard_v2/src/components/shell/NavRail.svelte`
- `src/dashboard_v2/src/components/shell/TopBar.svelte`
- `src/dashboard_v2/src/routes/+layout.svelte` — mounts AppShell
- `src/dashboard_v2/src/routes/home.svelte` — stub page
- `src/dashboard_v2/src/routes/memories.svelte` — stub page
- `src/dashboard_v2/src/routes/links.svelte` — stub page
- `src/dashboard_v2/src/routes/query.svelte` — stub page
- `src/dashboard_v2/src/routes/review.svelte` — stub page
- `src/dashboard_v2/src/routes/sessions.svelte` — stub page
- `src/dashboard_v2/src/routes/metrics.svelte` — stub page
- `src/dashboard_v2/src/routes/settings.svelte` — stub page

## Dependencies

_None_ — this is the foundation. All subsequent LKPR-1xx tickets depend on this.

## Design Ref

- **Spec:** §1 Global Shell, §8 Design Tokens
- **Mockups:** `design/visuals/page-home.png` (nav rail + top bar visible), `design/v7 - opus/Home (standalone).html`
- **Gaps resolved:** 6.1 — canonical 7-item nav list adopted

## Required Updates

- **CLAUDE.md**: [ ] Add `src/dashboard_v2/` directory structure to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] Add `lorekeeper-dev` note about dashboard v2 scaffold conventions
- **Backlog**: [ ] N/A

## Open Questions

- Should the SvelteKit project use `@sveltejs/adapter-static` for pure SPA output, or `@sveltejs/adapter-auto`? Recommend `adapter-static` since the dashboard is a standalone SPA served by FastAPI.
- Hash-based routing: implement a minimal SPA router or use a library like `svelte-spa-router`? Recommend a minimal custom router (<50 LOC) to avoid dependency — see LKPR-126.
- Tailwind v4 uses CSS-first config (`@theme` directive) instead of `tailwind.config.ts` — confirm which approach the team prefers. Epic references `tailwind.config.ts`; adapt to v4's `@theme` in `app.css` if needed.

## Notes

Foundation ticket — everything depends on this. Build first, test thoroughly, then unblock LKPR-123 through LKPR-125. The nav layout constants (76px rail, 60px top bar, 440–460px drawer) are used by every subsequent component; verify them once here rather than per-ticket.

## Next

**LKPR-123** — Toast + Confirm Dialog
