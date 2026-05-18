---
date: 2026-05-18
session_id: b419550c-63e3-4c72-b540-0c20bbb8c8fa
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/b419550c-63e3-4c72-b540-0c20bbb8c8fa.jsonl
topic: score-fix-redesign
task_type: build
---

## What was done
Fixed default insert score (1.0 → 5.0) so new memories start at a visible mid-range rather than near-invisible low tier. Wrote and ran `scripts/normalize_scores.py` to shift all existing memories by +4.0. Added dashboard improvements: live filter input with debounce, per-tier stats (high/mid/low counts), description subtitles in list, and a full flat-design CSS overhaul with smooth transitions.

## Decisions made
- Shift formula `min(10.0, old + 4.0)` — preserves relative ordering; maps old neutral (1.0) to new neutral (5.0)
- Stats computation moved out of `renderList()` into `loadMemories()` — single-pass, not recomputed on every keystroke
- Debounce added to filter input (200ms) — avoids full re-render on every character
- `--t: 0.15s ease` CSS variable — single point of control for all transitions
- Flat design: shadows removed, borders softened, `--radius: 6px` for gentler corners

## Corrections / discoveries
- At score 1.0, new memories contributed only `0.015` to hybrid search formula (`0.15 × score/10`) — made fresh inserts nearly invisible in search results until manually uprated
- Stats using five separate array passes → collapsed to one; was a real perf issue on 140+ memories
- Inline hex colors in stats → moved to CSS classes (`.stat-high`, `.stat-mid`, `.stat-low`)

## Lessons learnt
- **Changed default score without migrating existing data** → User had to point out: "need to normalize the old score, because we changed the starting point to 5 instead of 1". Agent changed orchestrator.py default but didn't think to write a migration script for the 140 existing memories at the old baseline. Rule: when changing any default value that affects existing stored data, always check whether a migration is needed.
- **Left previous session incomplete** → Session opened with "continue the work" — agent had not finished the prior session cleanly. Always summarize remaining work at session end.

## Proposed updates
- [x] memory: default score changed to 5.0; migration script logic; dashboard now has filter + stats
- [x] README: updated Memories tab description, added `LORE_DASH_RELOAD` to config table
- [ ] feedback: "when changing a default value, check if existing data needs migration", "summarize remaining work at session end"
