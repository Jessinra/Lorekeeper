---
id: LKPR-128
title: Relationship drawer — side-by-side memory cards with relation pill and per-page action footers
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 293
---

# [LKPR-128] Relationship drawer

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

When reviewing link suggestions (via `lore_get_suggestions`) or browsing existing links between memories, there is no way to see both memories side-by-side. The user must open each memory individually (via detail drawer) or make separate MCP calls. This makes it hard to evaluate whether a suggested link is correct, or to understand why two memories are related.

The spec (§2.2-B) describes a slide-in drawer showing two memory cards side by side with a relation pill between them, and context-sensitive action footers depending on which page opened the drawer.

## Solution

Build a `RelationshipDrawer` component — a slide-in panel (~640px wide) that displays two memories as side-by-side cards with a RelationPill in the center, and a footer whose buttons change based on the calling context (Links page, Review suggestions page, Review stale page).

### Drawer layout

Similar to MemoryDetailDrawer (LKPR-127): scrim overlay, slide-in from right, 640px wide (wider to accommodate two cards), full-height. White background, `box-shadow: -4px 0 12px rgba(0,0,0,0.1)`, `border-radius: 0`, 200ms CSS transition.

**Close:** × button in top-right of drawer, Escape key, click scrim.

### Header

Shows "Relationship" as title, with a subtitle line: `{source_title} ← {relation_label} → {target_title}` in muted gray (`#6b7280`).

### Body: Two memory cards + relation pill

Two cards laid out horizontally with a RelationPill between them. Each card:

- White background, `border: 1px solid #e5e7eb`, `border-radius: 8px`, padding 16px
- Width: calc(50% - 48px) to leave room for the center pill
- **Card inner sections:**
  - **Title** — memory title, font-weight 600, font-size 14px, truncate with ellipsis
  - **Meta strip** — NamespaceDot + score (ScorePill) + confidence bar, compact horizontal layout, font-size 11px
  - **Content preview** — first 3 lines of content in a light gray background (`#f9fafb`), `border-radius: 4px`, padding 8px, monospace font-size 12px, `overflow: hidden`, `text-overflow: ellipsis`. If content is longer, a "Show full" link opens the MemoryDetailDrawer for that memory.
  - **Description** — italicized description or "No description", font-size 12px, color `#6b7280`
  - **Click card to open detail drawer** — clicking either memory card closes the relationship drawer and opens the MemoryDetailDrawer for that specific memory.

Between the two cards: a centered vertical stack with the RelationPill (from LKPR-126) and direction arrows (→ or ↔ depending on symmetry).

### Footer: context-sensitive action buttons

The footer changes based on `page` prop:

| Page context         | Button 1                    | Button 2                    |
| -------------------- | --------------------------- | --------------------------- |
| `links`              | "Delete link" (red outline) | —                           |
| `review-suggestions` | "Accept" (green, `#16a34a`) | "Reject" (gray)             |
| `review-stale`       | "Refresh" (purple)          | "Delete link" (red outline) |

Footer layout: `position: sticky`, `bottom: 0`, `border-top: 1px solid #e5e7eb`, `padding: 12px 24px`, background white, `display: flex`, `justify-content: flex-end`, `gap: 8px`.

**Link page actions:**

- "Delete link" → `DELETE /api/links/{id}`, confirms via dialog, closes drawer on success.

**Review suggestions actions:**

- "Accept" → calls `lore_review_suggestion({suggestion_id, action: 'accept'})`, updates UI to show the link as accepted, disables both buttons.
- "Reject" → calls `lore_review_suggestion({suggestion_id, action: 'reject'})`, disables both buttons, visual change to show rejected (gray overlay).
- After accept/reject: brief success animation (green flash on the pill), then auto-close after 1.5s.

**Review stale actions:**

- "Refresh" → triggers re-evaluation of the relationship (API call that re-runs the link scoring), shows a spinner during evaluation.
- "Delete link" → same as Link page delete behavior.

### Empty / edge states

- If one memory is soft-deleted: show a strikethrough title and "Deleted" badge on that card, with orange border (`#fca5a5`).
- If content is empty: show "No content" placeholder in the content preview area.
- If the relation is `conflicts_with`: subtle red tint on both cards' borders (`#fecaca`).

### Data loading

Drawer receives a `sourceId` and `targetId` (or a `suggestionId` for review pages) as props. On open, it fetches full memory details for both IDs via `GET /api/memories/{id}` (or accepts them pre-loaded from the calling page if already available).

## Acceptance Criteria

- [ ] Drawer slides in from the right at ~640px width with scrim overlay
- [ ] Header shows "Relationship" with source → target subtitle
- [ ] Two memory cards render side-by-side with meta strip, content preview, description
- [ ] RelationPill renders centered between the two cards with correct color per type
- [ ] Clicking a memory card opens MemoryDetailDrawer for that memory (closes relationship drawer)
- [ ] Footer buttons change based on `page` prop: links, review-suggestions, review-stale
- [ ] "Delete link" confirms before calling API and closes drawer on success
- [ ] "Accept" calls accept API, shows visual confirmation, auto-closes
- [ ] "Reject" calls reject API, disables buttons, closes after 1.5s
- [ ] "Refresh" shows spinner, re-fetches link evaluation
- [ ] Soft-deleted memory shows strikethrough + "Deleted" badge
- [ ] Empty content shows "No content" placeholder
- [ ] Escape key closes the drawer

## Non-goals

- No drag-to-resize drawer
- No ability to edit the relationship type from this drawer (keyboard or form)
- No batch operations (one link at a time)
- No undo after delete

## Affected Files

**New:**

- `src/lorekeeper/dashboard/static/js/relation-drawer.js` — RelationshipDrawer module
- `src/lorekeeper/dashboard/static/css/relation-drawer.css` — two-card layout, footer per-page variants

**Modified:**

- `src/lorekeeper/dashboard/routes/links.py` — add `DELETE /api/links/{id}` endpoint
- `src/lorekeeper/services/link_store.py` — add `delete_link(id)` method
- `src/lorekeeper/dashboard/static/index.html` — add relationship drawer container div

## Dependencies

- LKPR-126 (ScorePill, NamespaceDot, RelationPill primitives) — used on the memory cards
- LKPR-127 (MemoryDetailDrawer) — clicking a card opens the detail drawer for that memory

Backend: `LinkStore.delete_link()`, `LinkSuggestionStore.update_suggestion_status()` must exist or be added.

## Required Updates

- **CLAUDE.md**: [ ] Add `static/js/relation-drawer.js` to project map, add `DELETE /api/links/{id}` to routes
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Notes

This drawer is the only place in the dashboard where two memories are shown side-by-side. The per-page footer pattern (derived from §2.2-B) allows a single drawer component to serve three different pages: Links, Review suggestions, and Review stale.

The auto-accept/reject feedback (green flash, auto-close) draws from the existing claude-mem suggestion-review UX pattern.

## Next

**LKPR-129** — Memories page (wires data table + filters + drawer)
