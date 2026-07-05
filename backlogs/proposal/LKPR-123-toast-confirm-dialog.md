---
id: LKPR-123
title: Toast + Confirm Dialog
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 288
---

# [LKPR-123] Toast + Confirm Dialog

## Problem

The dashboard v2 has no way to give user feedback after actions (save, delete, copy, accept/reject) or to confirm destructive operations. Every page from LKPR-129 onward needs both. Without these two components, every page would inline its own toast or dialog logic, creating inconsistencies in appearance, timing, and behavior.

The design spec defines two distinct overlay patterns:

- **Toast** — transient success/notification feedback, bottom-center, auto-dismiss
- **Confirm Dialog** — blocking destructive-action confirmation, centered modal, requires user acknowledgment

These must be built once, shared everywhere, and follow the spec's cross-cutting rules (§4): destructive actions confirm, reversible/lightweight actions toast.

## Solution

### 1. Toast store (`src/dashboard_v2/src/lib/toast.ts`)

A Svelte writable store that manages a queue of toast messages. Each toast:

- `id` — unique string (auto-generated)
- `message` — display text
- `type` — `success` | `error` | `info` (controls icon swatch color)
- `duration` — ms before auto-dismiss (default: 1800ms, per spec §2.8)
- `created_at` — timestamp for ordering

Export functions:

- `showToast(message, type?, duration?)` — push a toast, auto-dismiss after duration
- `dismissToast(id)` — manually dismiss a specific toast
- `toastStore` — readable store with the active queue

### 2. Toast component (`src/dashboard_v2/src/components/overlays/Toast.svelte`)

Renders the toast queue:

- Position: fixed, bottom-center, centered via flexbox
- Visual: dark pill (`#1a1a2e` background), white text, `~400px` max-width, pill-radius (`999px`), `control-radius` (`9px`) fallback
- Supports: optional icon swatch (colored to type), message text
- Entrance: fade-in + slide-up animation over ~200ms
- Exit: fade-out over ~200ms (CSS transition, triggered when removed from store)
- Auto-dismiss: after `duration` ms (default 1.8s), spec §2.8
- Manual dismiss: click on toast dismisses immediately
- Queue: shows one toast at a time; if multiple toasts are queued, show the latest, stacking older ones beneath (or replace — spec §2.8 notes only one toast is ever shown in mockups; decide queue behavior: single-display with sequential reveal)
- Uses `onMount` / `onDestroy` lifecycle for timer management

### 3. Confirm Dialog component (`src/dashboard_v2/src/components/overlays/ConfirmDialog.svelte`)

Blocking centered modal, spec §2.7:

- **Scrim:** fixed full-screen, dark (`rgba(0,0,0,0.4)`), click-to-close (cancels the dialog)
- **Card:** centered, ~400px wide, white, `card-radius` (14px), padding, elevation shadow
- **Icon swatch:** 40×40 colored circle with icon, color-matched to severity:
  - Neutral (soft-delete adjacent): gray (`#6b7280`)
  - Destructive (hard-delete, delete-link): red (`#dc2626`)
- **Title:** bold, `text-primary` (`#1a1a2e`)
- **Body copy:** descriptive text, `text-body` (`#3f3f52`)
- **Optional preview chip:** name/identity of the thing being deleted (e.g. memory title), rendered as a small pill
- **Actions:** `Cancel` (secondary, left) + destructive-confirm button (primary/danger, right)
- **Props:**
  - `open: boolean` — visibility control
  - `title: string`
  - `message: string`
  - `confirmLabel: string` (default "Delete")
  - `severity: 'neutral' | 'destructive'` (default `'destructive'`)
  - `itemName: string | null` (optional — shows preview chip)
  - `onConfirm: () => void` — callback when user confirms
  - `onCancel: () => void` — callback when user cancels
- **Keyboard:** `Escape` closes (cancels), `Enter` confirms when confirm button is focused
- **Focus trap:** on open, focus is trapped inside the dialog (first focusable element = Cancel button)
- **Animation:** fade-in scrim + scale-up card entrance over ~200ms

### 4. Integration with AppShell

Mount `Toast` in `AppShell.svelte` so it's available from every page. The `ConfirmDialog` is mounted per-page where needed (not globally — each page controls its own dialog state).

## Acceptance Criteria

- [ ] `showToast('Memory copied')` call renders a dark pill at bottom-center that fades in, auto-dismisses after ~1.8s, and fades out
- [ ] Multiple rapid `showToast` calls queue correctly (displays one at a time, shows next after current dismisses)
- [ ] Toast supports `success` (green icon), `error` (red icon), `info` (gray icon) types
- [ ] Clicking a toast dismisses it immediately
- [ ] `ConfirmDialog` renders centered card with scrim, title, body, icon swatch, and Cancel/Confirm buttons
- [ ] `severity='destructive'` shows red icon swatch and danger-styled confirm button
- [ ] `severity='neutral'` shows gray icon swatch
- [ ] `itemName` prop renders a preview chip identifying the item
- [ ] Clicking scrim or Cancel calls `onCancel` and closes
- [ ] Clicking Confirm calls `onConfirm` and closes
- [ ] `Escape` key cancels the dialog
- [ ] Focus is trapped inside the dialog when open
- [ ] Toast is mounted in `AppShell.svelte` and available on all pages
- [ ] Unit tests for toast store (add, dismiss, auto-dismiss, queue ordering)
- [ ] Unit tests for ConfirmDialog (open/close, keyboard events, callback firing)

## Non-goals

- No toast stacking/grouping for bulk operations (decide in LKPR-129 when bulk actions are built)
- No toast action buttons (e.g. "Undo") — spec shows text-only toasts
- No toasts for inline tooltip messages (separate pattern, not in spec)
- No ConfirmDialog for bulk actions (bulk confirm is a separate pattern, spec §2.6)
- No animation library — pure CSS transitions only

## Affected Files

**New:**

- `src/dashboard_v2/src/lib/toast.ts` — toast store/queue
- `src/dashboard_v2/src/components/overlays/Toast.svelte`
- `src/dashboard_v2/src/components/overlays/ConfirmDialog.svelte`

**Modified:**

- `src/dashboard_v2/src/components/shell/AppShell.svelte` — mount `<Toast />`

## Dependencies

- **LKPR-122** — AppShell must exist to mount Toast

## Design Ref

- **Spec:** §2.7 (Confirm Dialog), §2.8 (Toast), §4.1 (cross-cutting destructive-action rule)
- **Mockups:** `design/visuals/component-confirm-dialog.png` (hard-delete dialog), `design/v7 - opus/Home (standalone).html` (toast visible in demo)
- **Gaps resolved:** 6.6 — confirm dialog is used for hard-delete only (soft-delete toasts immediately, per spec §4.1)

## Required Updates

- **CLAUDE.md**: [ ] Add `src/dashboard_v2/src/lib/toast.ts` and overlay components to project map
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should the toast queue support grouping (e.g. "3 items deleted" instead of 3 sequential toasts)? Spec §2.8 notes the mockups only show one toast at a time — defer to LKPR-129 when bulk actions are built.
- What happens if a toast is shown while a ConfirmDialog is open? The toast should overlay above the dialog's scrim (higher z-index), since toasts are transient and dialogs are blocking.
- ConfirmDialog focus trap: should it trap focus to the dialog card only, or also allow tabbing to the browser chrome? Recommend full focus trap (standard modal pattern).

## Notes

These two components are required by nearly every subsequent ticket. Build them early, test edge cases (rapid toasts, dialog on mobile, keyboard navigation), and verify they work in isolation before any page integration.

## Next

**LKPR-124** — Command Palette (global ⌘K overlay)
