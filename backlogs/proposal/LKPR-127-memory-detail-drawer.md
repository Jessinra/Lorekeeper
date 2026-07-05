---
id: LKPR-127
title: Memory detail drawer — view/edit modes, scrim, meta row, danger zone
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 292
---

# [LKPR-127] Memory detail drawer

## Problem

The Memories tab currently only shows a table of memories. Clicking a row has no behavior beyond highlighting. Users have no way to inspect a memory's full content, edit its fields, delete it, or view its metadata — everything requires MCP tool calls. This makes the dashboard feel like a read-only viewer rather than a management tool.

The spec (§2.2-A) describes a slide-in drawer with two modes (view and edit) that provides full memory inspection and editing without navigating away from the list.

## Solution

Build a `MemoryDetailDrawer` component that slides in from the right edge of the screen when a user clicks a memory row in the Memories page (LKPR-129) or the Health decay candidates list (LKPR-88).

### Drawer layout

Opens as an overlay: a semi-transparent scrim (`rgba(0,0,0,0.3)`) covers the page behind while the drawer panel slides in from the right. The panel is ~440px wide, full-height, white background, with `box-shadow: -4px 0 12px rgba(0,0,0,0.1)`. CSS transition on `transform: translateX(...)` with 200ms ease.

### Sections (top to bottom)

**1. Scrim + close button** — clicking the scrim closes the drawer. A small × button in the top-right corner of the drawer panel also closes it.

**2. Header** — memory title (h2, font-size 18px, font-weight 600) with a status badge inline. Status badge is a small pill showing one of: `Active` (green, `#16a34a` bg), `Low confidence` (amber, `#d97706` bg), `Decaying` (red, `#dc2626` bg), or `Deleted` (gray, `#6b7280` bg, strikethrough title when `soft_deleted=true`).

**3. Meta row** — a horizontal strip below the header showing:

| Field       | Display                                    |
| ----------- | ------------------------------------------ |
| Namespace   | NamespaceDot + namespace label             |
| Created     | Formatted date (e.g. "Jun 15, 2026")       |
| Updated     | Formatted date (relative if <7d: "3d ago") |
| Score       | ScorePill component                        |
| Confidence  | Number out of 10 with small bar indicator  |
| Usage count | Number                                     |

Each meta item separated by a small vertical divider (`#e5e7eb`, height 16px).

**4. Body** (view mode)

- **Source type** — label showing `source_type` value (e.g. "observed", "user_stated"), styled as a small tag.
- **Description** — the memory's `description` field, or italicized "No description" placeholder.
- **Content** — full memory content in a scrollable container (max-height 300px, overflow-y auto), monospace font (`font-family: ui-monospace`), `font-size: 13px`, background `#f9fafb`, padding 12px, border-radius 8px, border `1px solid #e5e7eb`.

**5. Links section** — when the memory has linked memories, show a compact list:

- Each link: RelationPill + target memory title (clickable, closes current drawer and opens that memory's drawer)
- "N links" header with a toggle to expand/collapse
- If no links: show small muted text "No linked memories"

**6. Danger zone** (edit mode only) — a red-bordered section at the bottom of the body with:

- Border: `1px solid #fca5a5`, border-radius 8px, padding 16px, background `#fef2f2`
- Header: "Danger Zone" in red (`#dc2626`), font-size 14px, font-weight 600
- "Delete this memory" button — red outline button (`border: 1px solid #dc2626`, text `#dc2626`), with confirmation dialog (one more click to confirm)
- "Forget (soft-delete)" button — less prominent, orange outline
- Both buttons disabled when `soft_deleted=true` (show "Already deleted" badge instead)

**7. Footer** — swaps based on mode:

| Mode | Left button         | Right button            |
| ---- | ------------------- | ----------------------- |
| View | "Copy ID" (outline) | "Edit" (purple primary) |
| Edit | "Cancel" (outline)  | "Save" (purple primary) |

Footer is a `position: sticky`, `bottom: 0` bar with `border-top: 1px solid #e5e7eb`, `padding: 12px 24px`, background white, flexbox with `justify-content: flex-end`, `gap: 8px`.

### Edit mode

When the user clicks "Edit" in the footer, the drawer transitions from view to edit mode:

- Title becomes an `<input type="text">` field (font-size 18px, font-weight 600)
- Description becomes a `<textarea>` (font-size 14px, min-height 60px)
- Content becomes a larger `<textarea>` (monospace, font-size 13px, min-height 200px)
- Score becomes a numeric `<input type="number">` (min 0, max 10, step 0.5)
- Source type becomes a `<select>` dropdown
- Danger zone appears at the bottom
- Footer swaps to Cancel + Save

On save: `PATCH /api/memories/{id}` with the updated fields. On success, close drawer and refresh the memories list. On error, show an inline error message in the drawer body.

On cancel: restore original values and return to view mode. If any field was dirty, show a "Discard changes?" confirmation before reverting.

### Copy ID

Clicking "Copy ID" in view mode writes the memory's `lore_id` to `navigator.clipboard.writeText()` and briefly shows a "Copied!" tooltip on the button for 1.5 seconds.

### Keyboard

- `Escape` closes the drawer
- `Ctrl+Enter` or `Cmd+Enter` in edit mode triggers save

## Acceptance Criteria

- [ ] Drawer slides in from the right with 200ms CSS transition
- [ ] Scrim covers the page behind the drawer, clicking it closes the drawer
- [ ] Header shows title + correct status badge (Active/Low confidence/Decaying/Deleted)
- [ ] Meta row shows all 6 fields with correct formatting, ScorePill, and NamespaceDot
- [ ] View body shows source type tag, description, full content in scrollable monospace container
- [ ] Links section shows linked memories with RelationPill, expandable
- [ ] Edit mode converts title/description/content/score/source-type to inputs, shows danger zone
- [ ] Danger zone shows Delete + Forget buttons (disabled if already deleted)
- [ ] View footer has Copy ID (copies to clipboard) + Edit buttons
- [ ] Edit footer has Cancel (discard confirmation if dirty) + Save buttons
- [ ] Save sends `PATCH /api/memories/{id}`, refreshes list on success
- [ ] Escape key closes the drawer
- [ ] Ctrl/Cmd+Enter triggers save in edit mode
- [ ] Drawer is ~440px wide, full viewport height

## Non-goals

- No drag-to-resize drawer
- No undo after delete (soft-delete is reversible via API, but no undo toast)
- No inline editing of namespace or created/updated dates
- No batch editing (one memory at a time)
- No mobile-responsive drawer (works at ≥1024px)

## Affected Files

**New:**

- `src/lorekeeper/dashboard/static/js/memory-drawer.js` — MemoryDetailDrawer module
- `src/lorekeeper/dashboard/static/css/drawer.css` — drawer layout, animation, scrim styles

**Modified:**

- `src/lorekeeper/dashboard/routes/memories.py` — add `PATCH /api/memories/{id}` endpoint for editing memory fields
- `src/lorekeeper/dashboard/static/index.html` — add drawer container div if needed

## Dependencies

- LKPR-126 (ScorePill, NamespaceDot, RelationPill primitives) — used in the meta row and links section
- LKPR-129 (Memories page) — provides the row-click trigger that opens the drawer

PATCH endpoint depends on `MemoryStore.update_memory()` in the backend.

## Required Updates

- **CLAUDE.md**: [ ] Add `static/js/memory-drawer.js` and `routes/memories` PATCH endpoint to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should the drawer fetch memory details via `GET /api/memories/{id}` on open, or should the row data from the table be sufficient? (Prefer a dedicated GET endpoint for fresh data including links and scores.)
- What about very long content (>50KB)? Should we cap the displayed content in the scrollable container?

## Notes

The drawer pattern mirrors the existing slide-in behavior that claude-mem's dashboard uses. The two-mode (view/edit) design keeps the default experience clean while still providing power-user editing.

This component is triggered by row clicks in the Memories page (LKPR-129) and the decay candidates table in the Health tab (LKPR-88).

## Next

**LKPR-128** — Relationship Drawer (read-only memory cards + relation pill)
