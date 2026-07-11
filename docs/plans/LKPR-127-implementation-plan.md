---
id: LKPR-127
title: Memory detail drawer — implementation plan
type: plan
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-07-11
github_issue: 292
---

# [LKPR-127] Memory Detail Drawer — Implementation Plan

**Goal:** Build a `MemoryDetailDrawer` Svelte 5 component for Dashboard V2 that slides in from the right with view/edit modes, status badge, meta row, links section, danger zone, and clipboard copy.

**Branch:** `dashboard-revamp` (latest, with LKPR-126 UI primitives merged)

---

## Task 1: Design tokens + string constants

**Objective:** Add drawer-specific CSS variables to `app.css` and display strings to `strings.ts`.

**Files:**

- Modify: `src/dashboard_v2/src/app.css` — add `--color-drawer-*` tokens
- Modify: `src/dashboard_v2/src/lib/constants/strings.ts` — add `DRAWER_STRINGS`

**Step 1 — app.css tokens**

Add to the `@theme` block in `app.css`:

```css
/* Drawer (MemoryDetailDrawer) */
--color-drawer-scrim: rgba(0, 0, 0, 0.3);
--color-drawer-bg: #ffffff;
--color-drawer-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
--color-drawer-border: #e5e7eb;
--color-drawer-divider: #e5e7eb;
--color-drawer-code-bg: #f9fafb;
--color-drawer-code-border: #e5e7eb;
--color-drawer-danger-bg: #fef2f2;
--color-drawer-danger-border: #fca5a5;
--color-drawer-danger-text: #dc2626;
--color-drawer-status-active: #16a34a;
--color-drawer-status-low: #d97706;
--color-drawer-status-decaying: #dc2626;
--color-drawer-status-deleted: #6b7280;
```

**Step 2 — strings.ts constants**

Add `DRAWER_STRINGS` to `src/dashboard_v2/src/lib/constants/strings.ts`:

```ts
// ── Memory Detail Drawer (LKPR-127) ──────────────────────────────────────────

export const DRAWER_STRINGS = {
  /** aria-label on the close button */
  closeButtonAriaLabel: "Close drawer",
  /** aria-label on the drawer panel */
  drawerAriaLabel: "Memory detail",
  /** Status badge labels */
  statusActive: "Active",
  statusLowConfidence: "Low confidence",
  statusDecaying: "Decaying",
  statusDeleted: "Deleted",
  /** Danger zone section */
  dangerZoneHeader: "Danger Zone",
  dangerZoneDelete: "Delete this memory",
  dangerZoneForget: "Forget (soft-delete)",
  dangerZoneAlreadyDeleted: "Already deleted",
  /** Meta field labels */
  metaCreated: "Created",
  metaUpdated: "Updated",
  metaScore: "Score",
  metaConfidence: "Confidence",
  metaUsage: "Usage count",
  /** Links section */
  linksHeader: "Links",
  linksEmpty: "No linked memories",
  /** Body placeholders */
  noDescription: "No description",
  /** Footer */
  footerCopyId: "Copy ID",
  footerEdit: "Edit",
  footerCancel: "Cancel",
  footerSave: "Save",
  copyIdTooltip: "Copied!",
  /** Confirmation */
  discardConfirm: "Discard changes?",
} as const;
```

**Commit:** `[LKPR-127] chore: add drawer design tokens and string constants`

---

## Task 2: Create MemoryDetailDrawer.svelte — view mode

**Objective:** Create the drawer component with scrim overlay, slide-in panel, header with status badge, meta row, body section, links section, and view-mode footer.

**Files:**

- Create: `src/dashboard_v2/src/lib/components/overlays/MemoryDetailDrawer.svelte`

**Component structure:**

```svelte
<script lang="ts">
  import { tick } from 'svelte';
  import { DRAWER_STRINGS } from '$lib/constants/strings';
  import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
  import ScorePill from '$lib/components/ui/ScorePill.svelte';
  import NamespaceDot from '$lib/components/ui/NamespaceDot.svelte';
  import RelationPill from '$lib/components/ui/RelationPill.svelte';
  import type { MemoryData, LinkData } from './types'; // local types

  // ── Props ──
  interface Props {
    open: boolean;
    memory: MemoryData | null;
    links: LinkData[];
    onClose: () => void;
    onSave: (id: string, fields: Record<string, unknown>) => void;
    onNavigate: (targetId: string) => void;
  }
  let { open, memory, links = [], onClose, onSave, onNavigate }: Props = $props();

  // ── State ──
  let editMode = $state(false);
  let linksExpanded = $state(false);
  let copyTooltipVisible = $state(false);
  let drawerEl: HTMLElement | null = $state(null);
  let dirty = $state(false);

  // ── Derived ──
  let statusBadge = $derived(/* compute from memory.score, memory.soft_deleted */);
  let statusColor = $derived(/* color per status */);
  let formattedCreated = $derived(/* format date */);
  let formattedUpdated = $derived(/* relative if <7d else absolute */);

  // ── Handlers ──
  function handleClose() { /* close with discard confirm if dirty */ }
  async function handleCopyId() { /* navigator.clipboard.writeText */ }
  function handleKeydown(e: KeyboardEvent) { /* Escape closes, Cmd+Enter saves */ }
</script>

{#if open && memory}
  <OverlayScrim onclick={handleClose} />
  <div class="drawer" bind:this={drawerEl} role="dialog" aria-label={DRAWER_STRINGS.drawerAriaLabel}
    onkeydown={handleKeydown} tabindex="-1">
    <!-- ^^ svelte-ignore a11y_no_static_element_interactions ^^ -->

    <!-- Close button -->
    <button type="button" class="close-btn" onclick={handleClose}
      aria-label={DRAWER_STRINGS.closeButtonAriaLabel}>×</button>

    <!-- Header: title + status badge -->
    <h2 class="drawer-title">{memory.title ?? 'Untitled'}</h2>
    <span class="status-badge" style="background-color: {statusColor}">{statusBadge}</span>

    <!-- Meta row -->
    <div class="meta-row">
      <NamespaceDot namespace={memory.namespace} />
      <span>{memory.namespace}</span>
      <span class="meta-divider" aria-hidden="true"></span>
      <span>Created: {formattedCreated}</span>
      <span class="meta-divider" aria-hidden="true"></span>
      <span>Updated: {formattedUpdated}</span>
      <span class="meta-divider" aria-hidden="true"></span>
      <ScorePill score={memory.score} />
      <span class="meta-divider" aria-hidden="true"></span>
      <span>Confidence: {memory.confidence}/10</span>
      <div class="confidence-bar" style="width: {memory.confidence * 10}%"></div>
      <span class="meta-divider" aria-hidden="true"></span>
      <span>Usage: {memory.usage_count}</span>
    </div>

    <!-- Body: view mode -->
    <div class="body">
      <div class="source-tag">{memory.source_type}</div>
      <p class="description">{memory.description ?? DRAWER_STRINGS.noDescription}</p>
      <div class="content-block">{memory.content}</div>
    </div>

    <!-- Links section -->
    <div class="links-section">
      <button type="button" class="links-toggle" onclick={() => linksExpanded = !linksExpanded}>
        {links.length} {DRAWER_STRINGS.linksHeader}
      </button>
      {#if linksExpanded}
        {#if links.length > 0}
          {#each links as link}
            <button type="button" class="link-item" onclick={() => onNavigate(link.target_id)}>
              <RelationPill type={link.relation_type} />
              <span>{link.target_title}</span>
            </button>
          {/each}
        {:else}
          <p class="text-sm text-muted">{DRAWER_STRINGS.linksEmpty}</p>
        {/if}
      {/if}
    </div>

    <!-- Footer: view mode -->
    <div class="footer">
      <button type="button" class="btn-outline" onclick={handleCopyId}>
        {copyTooltipVisible ? DRAWER_STRINGS.copyIdTooltip : DRAWER_STRINGS.footerCopyId}
      </button>
      <button type="button" class="btn-primary" onclick={() => editMode = true}>
        {DRAWER_STRINGS.footerEdit}
      </button>
    </div>
  </div>
{/if}

<style>
  .drawer { /* fixed position, right: 0, top: 0, width: 440px, full height, white bg, shadow, z-index: 801, transform: translateX(0) by default, translateX(100%) when closed... */}
  /* ... */
</style>
```

**Key design decisions:**

- Reuse `OverlayScrim` from `$lib/components/ui/OverlayScrim.svelte` (z-index: 800)
- Drawer panel at z-index: 801 (above scrim)
- CSS transition on `transform: translateX(...)` with 200ms ease for slide-in
- `role="dialog"` + `aria-label` for accessibility
- `tabindex="-1"` and auto-focus on mount

**Step 1:** Create the `.svelte` file with view mode layout
**Step 2:** Add `<style>` block with CSS transitions and layout
**Step 3:** Build and verify with `svelte-check`

**Commit:** `[LKPR-127] feat: create MemoryDetailDrawer component with view mode`

---

## Task 3: Edit mode + danger zone + keyboard shortcuts

**Objective:** Add edit mode with form fields, danger zone, save/cancel, clipboard copy, and keyboard shortcuts.

**Same file:** `src/dashboard_v2/src/lib/components/overlays/MemoryDetailDrawer.svelte`

**Edit mode additions:**

```svelte
<!-- Edit mode form fields -->
{#if editMode}
  <!-- Danger zone -->
  <div class="danger-zone">
    <h3>{DRAWER_STRINGS.dangerZoneHeader}</h3>
    <button type="button" class="btn-danger" disabled={memory.soft_deleted}
      onclick={() => /* confirm then delete */}>
      {memory.soft_deleted ? DRAWER_STRINGS.dangerZoneAlreadyDeleted : DRAWER_STRINGS.dangerZoneDelete}
    </button>
    <button type="button" class="btn-danger-outline" disabled={memory.soft_deleted}
      onclick={() => /* confirm then forget */}>
      {DRAWER_STRINGS.dangerZoneForget}
    </button>
  </div>
{/if}

<!-- Footer: edit mode -->
{#if editMode}
  <div class="footer">
    <button type="button" class="btn-outline" onclick={handleCancel}>
      {DRAWER_STRINGS.footerCancel}
    </button>
    <button type="button" class="btn-primary" onclick={handleSave}>
      {DRAWER_STRINGS.footerSave}
    </button>
  </div>
{/if}
```

**Copy ID implementation:**

```ts
async function handleCopyId() {
  if (!memory) return;
  try {
    await navigator.clipboard.writeText(memory.lore_id);
    copyTooltipVisible = true;
    setTimeout(() => {
      copyTooltipVisible = false;
    }, 1500);
  } catch {
    /* fallback */
  }
}
```

**Keyboard shortcuts:**

```ts
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    handleClose();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    if (editMode) handleSave();
  }
}
```

**Discard confirmation:**

```ts
function handleClose() {
  if (editMode && dirty) {
    if (!confirm(DRAWER_STRINGS.discardConfirm)) return;
  }
  editMode = false;
  dirty = false;
  onClose();
}
```

**Step 1:** Add edit mode state, form fields, danger zone
**Step 2:** Add `handleSave` that calls `fetch('PATCH /api/memories/{id}')` or `onSave` callback
**Step 3:** Add `handleCancel` with dirty-check discard confirmation
**Step 4:** Add `handleCopyId` with clipboard API
**Step 5:** Add keyboard shortcut handler
**Step 6:** Build and verify with `svelte-check`

**Commit:** `[LKPR-127] feat: add edit mode, danger zone, copy ID, keyboard shortcuts`

---

## Task 4: TypeScript types + integration verification

**Objective:** Create shared types for the drawer's memory data shape and verify the component compiles.

**Files:**

- Create: `src/dashboard_v2/src/lib/components/overlays/types.ts`

```ts
export interface MemoryData {
  lore_id: string;
  title: string;
  description: string;
  content: string;
  namespace: string;
  source_type: string;
  score: number;
  confidence: number;
  usage_count: number;
  soft_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface LinkData {
  target_id: string;
  target_title: string;
  relation_type: string;
  // ... any other fields
}
```

**Step 1:** Create types.ts
**Step 2:** Run `npm run check` (svelte-check) to verify no type errors
**Step 3:** Run `npm run build` to verify build succeeds

**Commit:** `[LKPR-127] chore: add MemoryDetailDrawer types`

---

## Summary

| Task                        | Files                       | Commit                                                                     |
| --------------------------- | --------------------------- | -------------------------------------------------------------------------- |
| 1 — Design tokens + strings | `app.css`, `strings.ts`     | `[LKPR-127] chore: add drawer design tokens and string constants`          |
| 2 — View mode               | `MemoryDetailDrawer.svelte` | `[LKPR-127] feat: create MemoryDetailDrawer component with view mode`      |
| 3 — Edit mode + danger zone | `MemoryDetailDrawer.svelte` | `[LKPR-127] feat: add edit mode, danger zone, copy ID, keyboard shortcuts` |
| 4 — Types + verification    | `types.ts`, svelte-check    | `[LKPR-127] chore: add MemoryDetailDrawer types`                           |

**Total estimated new files:** 2 (MemoryDetailDrawer.svelte, types.ts)
**Total modified files:** 2 (app.css, strings.ts)
