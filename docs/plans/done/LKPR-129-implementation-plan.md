# LKPR-129: Memories Page Implementation Plan

**Goal:** Rebuild the /memories route in dashboard_v2 as a full-featured page with toolbar, filter chips, paginated DataTable, row-click → MemoryDetailDrawer, and URL state.

**Architecture:**

- **Backend**: Extend `GET /api/memories` with pagination/filter/sort params. Add `GET /api/memories/counts` and `GET /api/namespaces`.
- **Frontend**: `memories/+page.svelte` — orchestrates toolbar, FilterChip row, DataTable + Pagination, MemoryDetailDrawer, URL state.
- **No deps beyond LKPR-126/127** (already built: ScorePill, NamespaceDot, FilterChip, ToggleSwitch, EmptyState, MemoryDetailDrawer).

---

### Task 1: Backend — Add paginated `/api/memories` with filter/sort params

**Files:**

- Modify: `src/lorekeeper/dashboard/routes/memories.py` — add query params to `list_memories`
- Modify: `src/lorekeeper/dashboard/handler.py` — add `list_memories_paginated()`

**Step 1:** Add pagination params (`page`, `per_page`, `q`, `namespace`, `filter`, `sort`, `sort_dir`) to GET /api/memories with backward-compatible defaults.

**Step 2:** In handler, implement paginated query using MemoryStore SQL.

---

### Task 2: Backend — Add `/api/memories/counts` and `/api/namespaces`

**Files:**

- Modify: `src/lorekeeper/dashboard/routes/memories.py`
- Modify: `src/lorekeeper/dashboard/handler.py`

**Step 1:** `GET /api/memories/counts` returns `{all, needs_review, high_confidence, stale_30d}`.

**Step 2:** `GET /api/namespaces` returns distinct namespace list.

---

### Task 3: Frontend — API layer (`src/dashboard_v2/src/lib/api/memories.ts`)

**Files:**

- Create: `src/dashboard_v2/src/lib/api/memories.ts`
- Create: `src/dashboard_v2/src/lib/api/index.ts`

**Step 1:** `fetchMemories(params)` → paginated list.
**Step 2:** `fetchMemoryCounts()` → filter preset counts.
**Step 3:** `fetchNamespaces()` → namespace list.

---

### Task 4: Frontend — Memories page (`memories/+page.svelte`)

**Files:**

- Recreate: `src/dashboard_v2/src/routes/memories/+page.svelte`

Build the full memories page:

- Toolbar: search (debounced 300ms), namespace `<select>`, ToggleSwitch for deleted, +New stub button
- Filter chip row: All, Needs review, High confidence, Stale >30d (mutually exclusive, composable with search)
- DataTable: 7 columns (Title, NS, Score, Conf, Uses, Links, Updated) with sort
- Pagination: N-M of K, page buttons, page size selector
- Row click → MemoryDetailDrawer
- Empty state + skeleton loader
- URL query param sync via `$page.url`
- Loading/error/empty states

---

### Task 5: Frontend — Add MEMORIES_STRINGS to strings.ts

**Files:**

- Modify: `src/dashboard_v2/src/lib/constants/strings.ts`

Add strings for the memories page (search placeholder, filter chip labels, column headers, etc.)

---

### Task 6: Integration verification

**Step 1:** Build SvelteKit + verify no TS/lint errors.
**Step 2:** Run existing Vitest tests (Pagination, DataTable, MemoryDetailDrawer) — must be green.
**Step 3:** Run Python test suite — verify backend changes don't break existing dashboard tests.
