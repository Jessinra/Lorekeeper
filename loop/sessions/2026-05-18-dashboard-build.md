---
date: 2026-05-18
session_id: 665baf32-ea14-4a0f-9c12-2e540d733826
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/665baf32-ea14-4a0f-9c12-2e540d733826.jsonl
topic: dashboard-build
task_type: build
---

## What was done
Built the Lorekeeper dashboard from scratch: a FastAPI + single-page HTML app (`lorekeeper-dashboard` entrypoint) serving a browsable, sortable, searchable UI for all memories and links. Started with a flat list, then iterated through tabs (Memories, Links, Query, Detail), sortable columns, 2dp score formatting, hot-reload support, and the `after-changes` skill creation.

## Decisions made
- FastAPI chosen over Flask — async-native, matches existing lorekeeper server patterns
- Single-file HTML (`static/index.html`) read from disk on every request — trivial hot-reload for UI changes without server restart
- `LORE_DASH_RELOAD=1` env var enables Python hot-reload (uvicorn `reload=True`), default off — rationale: 16s Mem0/Chroma init cost makes accidental reloads expensive
- Detail view separated into its own tab after user feedback — avoids crowding the Memories tab
- `after-changes` skill created during this session to enforce code review + README check + commit discipline

## Corrections / discoveries
- Added `delete_link()` to `LinkStore` — was missing from the API surface
- `/api/links` endpoint needed to be a new route — not previously exposed by the MCP server

## Lessons learnt
- **Dived into implementation without plan mode** → User interrupted and said "use plan mode". Should always use Plan mode before implementing a non-trivial new feature.
- **Didn't run `after-changes` proactively** → User had to explicitly say "remember to review all your changes everytime you make some changes". Agent was not applying the review-then-commit discipline on its own.
- **package_skill.py wrote `.skill` artifact into the wrong directory** (lorekeeper project root instead of skills dir) → "why now theres a `.skill` file created whenever we run skill?" — need to pass an output directory or clean up after packaging.

## Proposed updates
- [x] CLAUDE.md: `after-changes` post-change checklist added as rule
- [x] memory: dashboard architecture, hot-reload behaviour, `after-changes` skill
- [ ] feedback: "use plan mode for non-trivial builds", "run after-changes proactively", "skill packaging output directory"

---

## Session continuation: 2026-05-18 UX redesign

### What was done
Full UX/UI redesign of the dashboard across two context windows. Iterative rounds of improvement driven by user and designer feedback:
1. Flat design system (CSS custom properties, pill tabs, score-badge tiers, metrics strip)
2. Refactored index.html (~1100 lines) into ES modules + css/styles.css
3. Detail page: view/edit mode split, delete buttons gated behind Edit
4. Memories table: links column, description subtitle in title cell
5. Detail links: grouped by relation_type using native `<details>` collapsibles
6. Config tab: live read/write of all LORE_* settings
7. Final: unified detail-grid layout for both view and edit modes (no layout shift)

### Decisions made
- **Callback registration pattern** for circular deps (memories ↔ detail): app.js imports both and wires after import via `registerDetailCallbacks` / `registerSelectMemory`
- **window.* exposure** for onclick handlers — ES modules don't expose to global scope
- **field() helper** for view/edit consistency: single template, same grid, only value widget swaps
- **Title stays in header h2 only** in view mode — avoids duplication with grid Title field
- **Config: in-memory mutation only** (`setattr(s, key, value)`) — env vars control persistence

### Corrections / discoveries
- `Edit` tool fails with "file modified since read" if another tool or edit changed the file — must re-read before editing
- `replace_all` conflicts when two identical strings exist — must add surrounding context
- ES module `onclick` handlers need `window.fn = fn` exports or they 404 at runtime
- FastAPI needs explicit `StaticFiles` mounts for `/css` and `/js` — they don't auto-serve subdirs

### Lessons learnt
- **Two-layout view/edit is the anti-pattern**: horizontal pill row vs vertical grid = jarring. Industry standard is one grid, swap only the value widget. The `field(label, viewHTML, editHTML)` helper is the clean way to do this.
- **Native `<details>`/`<summary>` for collapsibles** — zero JS, CSS chevron rotation on `[open]` state is all that's needed.
- **link_count on list endpoint**: compute in a single O(n) pass over all_links(), build a count dict, annotate rows — no extra API call needed.

### Proposed updates
- [x] memory: ES module architecture, view/edit consistency pattern, CSS design tokens, config tab pattern (all saved to lorekeeper)
