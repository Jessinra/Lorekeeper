---
id: LKPR-133
title: Query page — debug relevance search with 42/58 split layout, per-signal breakdown, result inspector
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 298
---

# [LKPR-133] Query page — debug relevance search with 42/58 split layout, per-signal breakdown, result inspector

## Problem

The current v1 Query tab (at `query.js`) is a simple search input + result cards with per-signal score pills. It has no split-panel layout, no result inspector, no stacked bar visualization of signal contributions, no auto-select of the first result, and no "Include deleted" toggle. It uses the standard `/api/search` endpoint which returns combined scores only — not the per-signal sub-scores needed for a debug tool.

The v7 design spec (§3.4) defines a dedicated **Query page** as an internal relevance-debugging tool. It exposes the hybrid ranker's raw signal breakdown (Semantic, Keyword, Mem score, Usage) that a normal search UI would hide — essential for developers debugging ranking quality.

## Solution

Build a **Query page** at `src/dashboard_v2/src/routes/query.svelte` with:

### Layout (spec §3.4)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Query                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ [Enter a search query to debug relevance…                    ] [Run] │ │
│  │ Limit: [10 ▼]  Min score: [0.10]  [Include deleted]                 │ │
│  │ Returns 12 memories + 8 linked · 143ms                               │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────── 42% ───────────┐─── 58% ──────────────────────────────┐   │
│  │ #1  Memory Title   0.87   │ Memory Title                          │   │
│  │ ▓▓▓▓▓▓▓▓░░░░      12 uses│ NS: default · Uses: 12                │   │
│  │ +4 linked               │                                        │   │
│  │                          │ ┌─── 0.87 ──┐                          │   │
│  │ #2  Second Memory  0.72  │ └───────────┘                          │   │
│  │ ▓▓▓▓▓▓░░░░░░        5 uses│                                        │   │
│  │ +2 linked               │ Memory content preview text goes here…  │   │
│  │                          │                                        │   │
│  │ #3  Third Memory   0.64  │ Why it ranked here:                    │   │
│  │ ▓▓▓▓▓░░░░░░░        3 uses│ Semantic  ██████████░░░  0.45          │   │
│  │ +0 linked               │ Keyword   ████░░░░░░░░  0.30            │   │
│  │                          │ Mem Score ██░░░░░░░░░░  0.15           │   │
│  │                          │ Usage     █░░░░░░░░░░░  0.10           │   │
│  │                          │                                        │   │
│  │                          │ Combined: 0.87 ▓▓▓▓▓▓▓▓▓▓▓▓▓           │   │
│  └──────────────────────────┴────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Composer bar

- **Text input** — full-width, placeholder "Enter a search query to debug relevance…", auto-focused on page load.
- **"Run query" button** — primary action button, triggers search. Also triggered by `Cmd+Enter` when input is focused.
- **Limit** — select dropdown: 5, 10, 20, 50. Default 10.
- **Min score** — number input, step 0.05, range 0.0–1.0. Default 0.10.
- **"Include deleted" toggle** — ToggleSwitch (spec §2.10), includes soft-deleted memories in results.
- **Result summary** — live text after query runs: "Returns N memories + M linked · Xms". Updates on each query.

### Split panel (42%/58%)

**Left panel (42%) — ranked result list:**

Each result row:

- **Rank #** — integer rank position (1, 2, 3…).
- **Title** — memory title, truncated if long.
- **Combined ScorePill** — 0–1.0 score, tinted green/amber/red per spec §2.3.
- **Stacked bar** — horizontal bar showing 4 signal contributions (Semantic, Keyword, Mem score, Usage) as colored segments. The bar's total width = combined score. Each segment is a distinct muted color:
  - Semantic: `#7c5cff` (purple)
  - Keyword: `#d97706` (amber)
  - Mem score: `#16a34a` (green)
  - Usage: `#6b7280` (gray)
- **Uses count** — "N uses" label.
- **+N linked** — number of linked memories. Clickable? Not in the mockup — just informational.

**Right panel (58%) — result inspector:**

Auto-populated with the first result on query load. Updates when clicking a left-panel row.

- **Header:** title (large), namespace dot + label, uses count.
- **Score badge:** big centered ScorePill with the combined score, same color scale.
- **Snippet:** memory content preview (first ~200 chars).
- **"Why it ranked here" breakdown:** one labeled progress bar per signal:
  - **Semantic** — progress bar width = semantic_score, right-side label shows value. Color: `#7c5cff`.
  - **Keyword** — progress bar width = keyword_score, right-side label. Color: `#d97706`.
  - **Mem score** — progress bar width = memory_score/10 \* combined (normalized), right-side label. Color: `#16a34a`.
  - **Usage** — progress bar width = log_usage_norm (normalized 0–1), right-side label. Color: `#6b7280`.
- Each progress bar has a label on the left and the numeric score on the right.

### Auto-select first result

On query completion, the first result is automatically selected and its data populates the right inspector. If there are no results, the inspector shows an empty state: "No results — try lowering the min score or searching for a different term."

### Empty states

- Pre-query: right panel shows "Run a query to see results" centered message.
- No results: left panel shows "No results" empty state; right panel shows "No results — try lowering the min score or searching for a different term."

### API dependencies

- `POST /api/v2/query/debug` — **new endpoint** that returns ranked results with per-signal sub-scores. Request shape:

  ```json
  {
    "query": "string",
    "limit": 10,
    "min_score": 0.1,
    "include_deleted": false
  }
  ```

  Response shape:

  ```json
  {
    "results": [
      {
        "rank": 1,
        "memory": {
          "id": "string",
          "title": "string",
          "namespace": "string",
          "score": 7.2,
          "usage_count": 12,
          "content": "string",
          "link_count": 4
        },
        "combined_score": 0.87,
        "semantic_score": 0.45,
        "keyword_score": 0.3,
        "memory_score": 0.15,
        "usage_score": 0.1
      }
    ],
    "total_results": 12,
    "total_linked": 8,
    "elapsed_ms": 143
  }
  ```

- **Mock data fallback**: If the `/api/v2/query/debug` endpoint doesn't exist yet, the query page should fall back to calling the existing `/api/search` endpoint and derive dummy per-signal scores from the combined score. The mock should:

  - Set `semantic_score = combined_score * 0.55`
  - Set `keyword_score = combined_score * 0.30`
  - Set `memory_score = combined_score * 0.10`
  - Set `usage_score = combined_score * 0.05`
  - Derive `total_linked = 0` (not available from search endpoint)
  - Derive `elapsed_ms = 0`

  This lets the UI be built and tested before the backend endpoint is ready. The mock path should be a simple boolean flag or API-version check in `api.ts`.

## Acceptance Criteria

- [ ] Composer bar renders: text input, Run button, Limit select, Min score input, Include deleted toggle
- [ ] Cmd+Enter triggers query from the text input
- [ ] Result summary line updates after each query with count and timing
- [ ] Left panel (42%) renders ranked result list with rank, title, ScorePill, stacked bar, uses, +N linked
- [ ] Stacked bar shows 4 colored segments proportional to per-signal scores
- [ ] Right panel (58%) renders result inspector with title, namespace, uses, big score badge, snippet, per-signal progress bars
- [ ] First result auto-selects on query load — populates right inspector
- [ ] Clicking a different left-panel row updates the right inspector
- [ ] "Include deleted" toggle adds soft-deleted memories to results
- [ ] Limit and Min score controls affect the API request
- [ ] Empty state renders when no results
- [ ] Pre-query state renders hint text in the inspector
- [ ] Mock data fallback works when `/api/v2/query/debug` endpoint is unavailable
- [ ] All progress bar colors match spec for each signal type

## Non-goals

- No memory editing from the query page (use Memories tab for that)
- No saving queries or query history
- No export of query results
- No comparison between two queries (side-by-side)

## Affected Files

**New:**

- `src/dashboard_v2/src/routes/query.svelte` — Query page: composer bar, 42/58 split panel, result list, inspector, empty states
- Backend: `src/lorekeeper/dashboard/routes/query.py` — new `/api/v2/query/debug` endpoint returning per-signal sub-scores

**Modified:**

- `src/dashboard_v2/src/lib/api.ts` — add `runDebugQuery()` method with mock data fallback

## Dependencies

- **LKPR-126** (UI primitives) — ScorePill, NamespaceDot, ToggleSwitch
- **LKPR-125** (DataTable + pagination) — pagination may be needed if result counts become large (defer for now)
- **LKPR-122** (Scaffold, shell, design tokens) — app shell and nav rail

## Required Updates

- **CLAUDE.md**: [ ] Add `routes/query.svelte` and `routes/query.py` to project map under dashboard v2
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] Update dashboard-v2-epic.md progress tracker to mark LKPR-133 as done

## Notes

The v1 `query.js` uses the existing `/api/search` endpoint which returns a `relevance` object with `combined_score`, `semantic_score`, `keyword_score` — so the per-signal data is technically already available from the search endpoint, just not broken out as a separate debug endpoint. The new `/api/v2/query/debug` endpoint exists to provide a cleaner contract (separate from the product search used by the Memories tab) and to add the `usage_score` signal which the current search doesn't expose.

The 42%/58% split ratio must be exact. Use CSS `grid-template-columns: 42fr 58fr` or equivalent. Do not fudge to 40/60 or 50/50.

The stacked bar in the left panel should render as a single `<div>` with colored segments using `display: flex`. Each segment's width = `(per_signal_score / combined_score) * 100%` of the bar. If combined_score is 0, show the bar as empty (all gray or no fill).

The mock data fallback is intentional — it lets the Svelte page be built, reviewed, and merged independently of the backend endpoint, which may land in a later sprint if the engineering team is backlogged.

## Next

**LKPR-134** — Home page (health ring, stat tiles, activity feed)
