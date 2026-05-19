---
date: 2026-05-19
session_id: 672c65ae-5f6c-4a13-8da5-9bb269789eba
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/672c65ae-5f6c-4a13-8da5-9bb269789eba.jsonl
topic: dashboard-dedup-bugfix
task_type: debug
---

## What was done
Three issues resolved in one session. (1) Dashboard refresh button added with auto-refresh (30s interval) after user noticed memories weren't appearing without manually reloading. (2) Timezone display bug fixed — `fmtDate` was slicing raw ISO strings (UTC) instead of converting to local time. (3) Critical duplicate links and duplicate memories bug found and fixed: no UNIQUE constraint existed on `memory_links` or `memories`, causing silent accumulation of duplicates across many sessions.

## Decisions made
- Dashboard auto-refresh interval: 30s via `setInterval` in `app.js`
- Duplicate cleanup strategy: keep highest-score memory per title; keep oldest link per source+target+type pair
- `_migrate()` runs at startup to clean existing dupes and add UNIQUE indexes — ensures all future inserts are protected
- Exact-title guard added in `_insert_one_memory` *before* semantic dedup (which only searched top 5, missing exact matches outside that window)

## Corrections / discoveries
- `memory_links` had no UNIQUE constraint on `(source_memory_id, target_memory_id, relation_type)` — every `insert_link` could silently duplicate. 298 duplicate links removed.
- Memory semantic dedup used `limit=5` in search — any exact title match outside the top 5 would slip through. 7 duplicate memories found and removed.
- DB deduplication fixed in `_migrate()` + new UNIQUE indexes. Memory title dedup fixed in `_insert_one_memory` with an exact-title lookup before semantic search.
- `fmtDate` was slicing the ISO string directly — this always showed UTC regardless of system timezone. Fix: `new Date(iso)` + read local parts via `.getFullYear()`, `.getMonth()`, etc.

## Lessons learnt
- **User asked "how did you check for unique earlier?"** → User wanted to understand the SQL technique, not just the result. **Principle:** When fixing a database-level bug, briefly explain the diagnostic query — `GROUP BY ... HAVING COUNT(*) > 1` is not obvious and worth sharing.

## Good patterns observed
- **Root-cause + symptom fix together** → Cleaned existing 298 duplicate links AND added the UNIQUE index in the same commit. Didn't just patch the code path without fixing existing data. **Principle:** Database constraint bugs require both a migration (fix existing data) and a schema change (prevent future occurrences).
- **Investigated systematically** → DB query first (how many dupes?) → schema check (what constraint exists?) → code (where does insert happen?) → fix in correct layer. **Principle:** For data bugs, always check the actual DB state before guessing the code cause.

## What I learned about the user
- **"investigate this bug, see why it shows duplicate links"** → User gives terse debug prompts and expects the agent to own the full investigation without step-by-step hand-holding. They trust the agent to find the root cause, not just apply a surface fix.
- **"2 bugs need fix: number links not showing, timezone not showing"** → User observes bugs visually, reports them as bullet points. They don't debug code — that's the agent's job.
