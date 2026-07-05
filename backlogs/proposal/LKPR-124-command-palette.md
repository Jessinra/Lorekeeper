---
id: LKPR-124
title: Command Palette
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 289
---

# [LKPR-124] Command Palette

## Problem

The dashboard has no quick-navigation or global command interface. Users must click through the nav rail to switch pages, and there is no way to search for memories, jump to specific pages, or trigger actions without navigating to the right page first.

The design spec (§2.9) calls for a global ⌘K (or Ctrl+K) palette that opens from any page — reminiscent of VS Code, Linear, or Stripe's command palettes. It provides three functions:

- **Jump to** — navigate to any page (Home, Memories, Links, etc.)
- **Open memory** — search memories by title, preview subtitle
- **Actions** — trigger global commands (new memory, run sweep, export backup)

The trigger already exists in the TopBar (built in LKPR-122). This ticket builds the palette itself.

## Solution

### 1. Command Palette component (`src/dashboard_v2/src/components/overlays/CommandPalette.svelte`)

Spec §2.9:

- **Trigger:** `⌘K` / `Ctrl+K` global keyboard shortcut and click on TopBar search trigger
- **Position:** centered modal, `640px` wide, over a blurred/dimmed scrim (see spec §1 layout constants)
- **Scrim:** full-screen, `rgba(0,0,0,0.4)`, click-to-close, optional backdrop-blur

**Input row:**

- Search icon (leading)
- Live text `<input>` (auto-focused on open, `placeholder="Search or jump to…"`)
- Trailing keyboard hint: `esc` label

**Result groups (empty query):**

- `Recent` — last 3–5 visited pages/states (may be stored in localStorage)
- `Jump to` — all 7 nav destinations (Home, Memories, Links, Query, Review, Sessions, Metrics) + Settings
- `Actions` — global commands: New memory (`N`), Run sweep (`S`), Export backup (`B`)

**Result groups (non-empty query):**

- `Jump to` — filter nav destinations by substring match on name
- `Memories` — filter local memory cache by title substring match (initially stubbed; real search endpoint integration deferred to post-LKPR-129)
- `Actions` — filter global commands by name
- Groups with zero matches are hidden entirely

**Each result row:**

- Icon swatch (colored circle with single character or glyph)
- Title (bold)
- Subtitle (muted, smaller)
- Optional trailing keyboard shortcut hint (e.g. `N`, `S`, `B`)

**Keyboard navigation:**

- `↑` / `↓` — move selection (wraps at top and bottom)
- `Enter` — select highlighted row (triggers action/toast)
- `Esc` — close palette
- Typing filters results live (debounced, ~150ms)

**Selection behavior:**

- Navigating to a page closes the palette and calls the router (or triggers a `navigate` callback)
- Selecting an action fires the action (may show a toast, e.g. "Opening Memories")
- Selecting a memory fires a callback (opens memory search results — stubbed to show a toast in v1)

**Empty state (no results):**

- Icon + "No results for '{query}'" + hint text below
- No reopen-hint pill (see spec §2.9 build note — drop the prototype affordance)

### 2. Command registration / store (`src/dashboard_v2/src/lib/commands.ts`)

A typed registry of available commands. Each command:

```ts
interface Command {
  id: string;
  group: "jump" | "recent" | "memory" | "action";
  title: string;
  subtitle: string;
  iconSwatch: string;
  shortcut?: string; // keyboard hint label
  action: () => void; // callback
}
```

Functions:

- `registerCommand(cmd: Command)` — add commands (extensible for dynamic memory results)
- `searchCommands(query: string): Command[]` — filter by substring match on title + subtitle
- `getGroupedCommands(query: string): Record<string, Command[]>` — group results for rendering

Default commands registered on init:

- Jump to: 7 nav pages + Settings
- Actions: New memory (`N`), Run sweep (`S`), Export backup (`B`)
- Stub for memory results (empty array initially)

### 3. Keyboard shortcut listener (`src/dashboard_v2/src/lib/hotkeys.ts`)

A lightweight global keyboard shortcut manager:

- Listens for `Meta+k` (macOS) / `Ctrl+k` (Windows/Linux) to toggle palette open/closed
- Listens for `Escape` when palette is open to close it
- Prevents default browser behavior for these combos
- Mounted once in `AppShell.svelte`

### 4. Integration with AppShell

- Mount `<CommandPalette>` in `AppShell.svelte` (available on every page)
- Wire TopBar search trigger click to toggle palette open state
- Hotkey listener registered in AppShell's `onMount`

## Acceptance Criteria

- [ ] Pressing `⌘K`/`Ctrl+K` opens the palette with auto-focused input
- [ ] Pressing `Esc` closes the palette
- [ ] Empty query shows 3 groups: Recent, Jump to, Actions — each with correct items
- [ ] Typing a query filters all groups by substring match (case-insensitive)
- [ ] Groups with zero matches are hidden
- [ ] `↑`/`↓` moves selection, wrapping at top/bottom
- [ ] `Enter` on a selected row fires its action and closes the palette
- [ ] Clicking "New memory" (or pressing `N`) fires the action and shows a toast (stub)
- [ ] Clicking empty scrim closes the palette
- [ ] Palette is 640px wide, centered, with blurred/dimmed scrim
- [ ] Search input is auto-focused on open
- [ ] Typing is debounced (~150ms) to avoid jank
- [ ] Empty state renders when no results match: "No results for '{query}'"
- [ ] TopBar search trigger click opens the palette
- [ ] Palette can be opened/closed multiple times without errors
- [ ] Unit tests for command filtering, search, keyboard selection

## Non-goals

- No real memory search backend integration (stub with empty state — real integration deferred to LKPR-129 when the Memories API exists, see spec §6.11)
- No recent-visited persistence (localStorage stub — wire up in LKPR-129 or later)
- No animation library for entrance — pure CSS transitions (fade + scale, matching ConfirmDialog pattern)
- No fuzzy search — plain substring match is sufficient for v1 (defer to v2 if user feedback demands it)
- No drag-to-reorder commands
- No mobile/touch-specific palette (SvelteKit SPA targets desktop primarily)

## Affected Files

**New:**

- `src/dashboard_v2/src/components/overlays/CommandPalette.svelte`
- `src/dashboard_v2/src/lib/commands.ts` — command registry
- `src/dashboard_v2/src/lib/hotkeys.ts` — global keyboard shortcut listener

**Modified:**

- `src/dashboard_v2/src/components/shell/AppShell.svelte` — mount `<CommandPalette />` and register hotkeys
- `src/dashboard_v2/src/components/shell/TopBar.svelte` — wire search trigger to open palette

## Dependencies

- **LKPR-122** — AppShell and TopBar must exist for integration
- **LKPR-123** — Toast component is used to show "Opening X" feedback on selection

## Design Ref

- **Spec:** §2.9 (Command Palette), §3.9 (page ref), §1 layout constants (640px width)
- **Mockups:** `design/visuals/page-command-palette.png`, `design/v7 - opus/Command Palette (standalone).html`
- **Gaps resolved:** 6.11 — stubbed with local list initially; real search endpoint deferred to post-LKPR-129

## Required Updates

- **CLAUDE.md**: [ ] Add overlay components and lib files to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should the palette blur the background or just dim it? Spec says "blurred/dimmed scrim" — recommend `backdrop-filter: blur(2px)` for production feel, with a `@supports` fallback to `rgba(0,0,0,0.4)` for browsers that don't support backdrop blur.
- Recent visited: should this persist to localStorage or be session-scoped? Start session-scoped (reset on page reload), revisit if retention is requested.
- Memory results in the palette: should we search client-side from a cached list, or hit a server endpoint? Defer — start with empty stub list, wire to real search after LKPR-129.

## Notes

The command palette is a signature UI element — make the animation feel snappy (150ms transitions, no delays). The VS Code/Linear palette is the quality target. Test with rapid open/close cycles to ensure no z-index or focus leaks.

## Next

**LKPR-125** — Data Table + pagination (sortable table, pagination footer, empty state)
