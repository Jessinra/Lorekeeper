# LKPR-122 — Scaffold, shell, design tokens

**Date:** 2026-07-07  
**Branch:** `dashboard-revamp` (origin already has planning commits — check it out, do not create new)  
**Output:** `src/dashboard_v2/` — SvelteKit 5 + Tailwind v4 + TypeScript scaffold

---

## Files to create

| File                                                    | Purpose                                                                   |
| ------------------------------------------------------- | ------------------------------------------------------------------------- |
| `src/dashboard_v2/package.json`                         | Svelte 5, SvelteKit, Tailwind v4, TypeScript deps                         |
| `src/dashboard_v2/svelte.config.js`                     | adapter-static, SPA fallback                                              |
| `src/dashboard_v2/vite.config.ts`                       | SvelteKit Vite plugin config                                              |
| `src/dashboard_v2/tsconfig.json`                        | strict TS preset                                                          |
| `src/dashboard_v2/tailwind.config.ts`                   | Design tokens from spec §8 (AC-required file)                             |
| `src/dashboard_v2/app.html`                             | HTML shell with `<div id="app">` mount                                    |
| `src/dashboard_v2/src/app.css`                          | `@import "tailwindcss"` + `@config` + `@theme` override + global defaults |
| `src/dashboard_v2/src/components/shell/AppShell.svelte` | 76px nav rail + 60px top bar + `<slot>`                                   |
| `src/dashboard_v2/src/components/shell/NavRail.svelte`  | 7 nav items + Settings at bottom                                          |
| `src/dashboard_v2/src/components/shell/TopBar.svelte`   | breadcrumb + ⌘K search trigger button                                     |
| `src/dashboard_v2/src/routes/+layout.svelte`            | Mounts AppShell, wraps all routes                                         |
| `src/dashboard_v2/src/routes/+page.svelte`              | Home stub (h1 + placeholder text)                                         |
| `src/dashboard_v2/src/routes/memories/+page.svelte`     | stub                                                                      |
| `src/dashboard_v2/src/routes/links/+page.svelte`        | stub                                                                      |
| `src/dashboard_v2/src/routes/query/+page.svelte`        | stub                                                                      |
| `src/dashboard_v2/src/routes/review/+page.svelte`       | stub                                                                      |
| `src/dashboard_v2/src/routes/sessions/+page.svelte`     | stub                                                                      |
| `src/dashboard_v2/src/routes/metrics/+page.svelte`      | stub                                                                      |
| `src/dashboard_v2/src/routes/settings/+page.svelte`     | stub                                                                      |

No existing files touched.

---

## Decisions

### Tailwind v4 config approach

Ticket's open question: `tailwind.config.ts` (AC requirement) vs CSS-first `@theme` (v4 native).  
**Decision:** Both. Keep `tailwind.config.ts` to satisfy the AC letter; use `@theme` in `app.css` as primary token source (v4 CSS-first is more complete and avoids partial compat mode). `app.css` has `@import "tailwindcss"` + `@config "./tailwind.config.ts"` + `@theme` block with all token overrides.

### Routing

SvelteKit's file-based routing with adapter-static (`fallback: 'index.html'`). No custom hash router — per non-goals, that's LKPR-126 territory. Routes at `/`, `/memories`, `/links`, etc.

### FastAPI wiring

Out of scope for this ticket. Build output at `src/dashboard_v2/build/` but FastAPI not updated to serve it here.

### CI

No new npm/node CI steps in this ticket. Dashboard_v2 build check is a follow-on.

---

## Icon approach

NavRail needs icons for Home, Memories, Links, Query, Review, Sessions, Metrics, Settings.  
Looking at the mockup: uses simple SVG icons (house, grid, network, search, inbox, clock, bar-chart, cog).  
**Decision:** Inline SVG strings in NavRail.svelte — zero external dep, zero bundle size. No icon lib.

---

## Active nav state

NavRail reads `$page.url.pathname` (SvelteKit store) to determine active item.  
Active: `bg-brand-tint text-brand font-semibold`. Hover inactive: `bg-gray-100`.

---

## Verification after build

1. `npm install && npm run check` (TypeScript check) — no errors
2. `npm run dev` — server starts, nav shell visible at localhost
3. Visual compare: nav rail 76px, top bar 60px, layout matches `design/visuals/page-home.png`

---

## No changes to

- Python source (`src/lorekeeper/`)
- `server.py`
- Any existing dashboard code
- CI workflows (for now)
- `pyproject.toml`
