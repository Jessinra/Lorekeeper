---
id: LKPR-130
title: Sessions page — day-grouped timeline, session cards, stacked drawer navigation
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 295
---

# [LKPR-130] Sessions page — day-grouped timeline, session cards, stacked drawer navigation

## Problem

The current v1 Sessions tab (at `sessions.js`) renders sessions as a flat table with inline expandable detail rows. There's no day-grouped timeline, no session cards showing task badge/title/time/duration/memory count in a glanceable format, and no drawer-based drill-down. Navigating from a session to a memory it produced requires switching to the Memories tab — there's no layered drawer pattern.

The v7 design spec (§3.6) defines a completely new Sessions page: a day-grouped vertical timeline of session cards, search by session ID/topic, task-type filter chips, and a SessionDrawer that can stack a MemoryDetailDrawer on top for layered drill-down.

## Solution

Build a **Sessions page** at `src/dashboard_v2/src/routes/sessions.svelte` with:

### Layout (spec §3.6)

```
┌──────────────────────────────────────────────────┐
│ [Search by session ID or topic…]   [All] [build] │
│                                    [debug][review]│
│                                    [design]       │
├──────────────────────────────────────────────────┤
│                                                    │
│  Today                                             │
│  ┌─────────────────────────────────────────────┐  │
│  │ [build] Refactored auth middleware 09:15 45m │  │
│  │         3 memories · a1b2c3d4              │  │
│  ├─────────────────────────────────────────────┤  │
│  │ [debug] Fixed API timeout regression 14:30  │  │
│  │         1h12m · 5 memories · e5f6g7h8      │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  Yesterday                                         │
│  ┌─────────────────────────────────────────────┐  │
│  │ [review] PR #142 code review      10:00 35m │  │
│  │         2 memories · i9j0k1l2              │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
└──────────────────────────────────────────────────┘
```

1. **Search bar** — free-text input filtering by session ID (substring match on the full hex string) or topic.
2. **Task-type filter chips** — row of pill chips: `All`, `build`, `debug`, `review`, `design`. Each chip shows a live count of sessions of that type. Click toggles exclusive filter.
3. **Day-grouped vertical timeline** — sessions grouped under a day header (Today, Yesterday, Monday, etc.). Each group rendered with a vertical timeline line + dot marker on the left.
4. **Session card** — white card per session containing:
   - Task badge (colored chip: build=green, debug=amber, review=purple, design=blue)
   - Session title/topic
   - Start time + duration (formatted as "09:15 · 45m")
   - Memory count (number of memories created in session)
   - Monospace session ID (first 8 chars)
5. **Empty state** — "No sessions match this filter" centered message when no results.

### SessionDrawer (spec §2.2-B variant)

Click a session card → slides in from right (~440–460px):

- **Header:** title, task badge, duration chip, close button
- **Meta row:** session ID (full, copyable), date/time, reflection link
- **Summary section:** the session's `what_was_done` / summary text
- **Memory list:** each memory rendered as a compact card (title, short description, score pill). Click a memory card → opens the shared **MemoryDetailDrawer** (from LKPR-127) **stacked on top** — same drawer component, same view/edit behavior as the Memories page.
- **Footer:** "Copy session ID" button → toast confirmation.

### Drawer stacking (spec §2.2 stacking rule)

When a memory is opened from within the SessionDrawer, the MemoryDetailDrawer layers on top with a higher z-index and its own scrim. Closing the MemoryDrawer reveals the SessionDrawer intact beneath — not the base page.

### API dependencies

- `GET /api/sessions?q=&task=&page=` — paginated sessions with task-type filter support. Existing `/api/sessions` returns all sessions; the v2 mount needs `q` (search) and `task` (task-type filter) query params and pagination.
- `GET /api/sessions/:id` — single session with its memories list. Existing `/api/sessions/:id` works but needs to include the `memories` array (memory IDs, titles, descriptions, scores).
- Uses existing `/api/reflections` for reflection detail linking.

## Acceptance Criteria

- [ ] Sessions page renders day-grouped vertical timeline from API data
- [ ] Search by session ID (substring on hex) filters the list
- [ ] Search by topic words filters the list
- [ ] Task-type filter chips show live counts and toggle active state
- [ ] Active filter chip clears to "All" when re-clicked
- [ ] Session card shows: task badge, title, time, duration, memory count, first-8 session ID
- [ ] Clicking a session card opens the SessionDrawer with full details
- [ ] SessionDrawer shows memory list; clicking a memory opens MemoryDetailDrawer stacked on top
- [ ] Closing the top (memory) drawer reveals the session drawer underneath
- [ ] Closing the session drawer returns to the timeline
- [ ] Empty state renders when no sessions match filter
- [ ] "Copy session ID" button in drawer copies to clipboard + shows toast
- [ ] Auto-refresh on tab activation (same lazy-load pattern as Memories)

## Non-goals

- No edit/delete actions on sessions (read-only format)
- No inline session creation (sessions are created by `/reflect` elsewhere)
- No infinite scroll — use standard pagination (50/page) for now; revisit if users have 1000+ session log

## Affected Files

**New:**

- `src/dashboard_v2/src/routes/sessions.svelte` — Sessions page: timeline, search, filter chips, session cards
- `src/dashboard_v2/src/components/drawers/SessionDrawer.svelte` — Session detail drawer: header, meta, summary, memory list

**Modified:**

- `src/dashboard_v2/src/routes/links.svelte` — may need nav rail update if Sessions link was missing
- `src/dashboard_v2/src/lib/api.ts` — add `fetchSessions()`, `fetchSessionDetail()` methods
- Backend: `src/lorekeeper/dashboard/routes/reflections.py` — enhance `/api/sessions` to support `q`, `task` query params and pagination
- Backend: `src/lorekeeper/dashboard/routes/reflections.py` — enhance `/api/sessions/:id` to return `memories` array

## Dependencies

- **LKPR-127** (MemoryDetailDrawer) — the stacked memory drawer must exist before Sessions can use it
- **LKPR-126** (UI primitives) — ScorePill, NamespaceDot, FilterChip for session cards
- **LKPR-125** (DataTable + pagination) — pagination component may be reused if session list gets long
- **LKPR-122** (Scaffold, shell, design tokens) — app shell and nav rail must exist

## Required Updates

- **CLAUDE.md**: [ ] Add `routes/sessions.svelte` and `components/drawers/SessionDrawer.svelte` to project map under dashboard v2
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] Update dashboard-v2-epic.md progress tracker to mark LKPR-130 as done

## Notes

This ticket depends on the stacked-drawer pattern (spec §2.2 stacking rule) which is unique to the Sessions page. Build and verify the stacking behavior with a clean test case before wiring real data — it's easy to get z-index wrong.

The backend `GET /api/sessions` endpoint should accept optional `query` (searches session_id + topic), `task` (task_type filter), `page` and `page_size` params. The existing `/api/sessions` returns all rows unfiltered; the v2 endpoint needs filtering and pagination for non-trivial session logs.

## Next

**LKPR-131** — Review Inbox (two-tab bulk select, inline actions)
