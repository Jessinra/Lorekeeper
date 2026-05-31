---
id: LKPR-52
title: Agent query dedup — cache repeated lore_search calls
type: enhancement
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-05-31
---

# [LKPR-52] Agent query dedup — cache repeated lore_search calls

## Problem

Agents make many `lore_search` calls across sessions. In practice, the same or nearly-identical queries get repeated — especially from cron jobs and PM workflows. Each call hits the vector DB, BM25, and re-ranker. With inference getting cheaper (cache economics) the bottleneck shifts to agent UX: agents waste time and tokens re-searching what they already found.

## Solution

A lightweight result cache on `lore_search`. Keep it minimal:

- **LRU cache in SQLite** (no new infra) — keyed by query + namespace + freshness TTL
- On cache hit within TTL (e.g. 5min), return staled results with a `cached: true` flag
- On cache miss, run normally and store the result
- Cache busted on any `lore_insert`/`lore_update` in the same namespace (data changed, results could be stale)
- Configurable TTL per call: `lore_search(query="...", cache_ttl=300)` — default 0 means no caching

No complex cache warming, no distributed cache, no Redis. Just a simple SQLite table with a cleanup job.

## Acceptance Criteria

- [ ] Repeated identical `lore_search` calls within TTL return cached results (identical except `cached: true` flag)
- [ ] `lore_insert`/`lore_update` in the same namespace clears the cache for that namespace
- [ ] `lore_search(..., cache_ttl=0)` always bypasses cache
- [ ] Old cache entries cleaned up on a schedule or on write (don't let it grow unbounded)
- [ ] All existing tests pass

## Affected Files

**Backend:**

- `src/lorekeeper/services/search.py` — add cache check layer
- `src/lorekeeper/services/link_store.py` — new cache table in SQLite
- `src/lorekeeper/config.py` — `LORE_CACHE_TTL_DEFAULT`, `LORE_CACHE_MAX_ENTRIES`

**Dashboard (if applicable):**

- `_none_` — pure backend change

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] N/A — no architectural changes
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A — no skill interface changes (cache is transparent with opt-out)
- **Backlog**: [ ] N/A

## Open Questions

- Should the cache survive process restarts? (Yes if SQLite-persisted — that's free)
- Should we expose cache stats via `lore_health` or similar?

## Notes

Filed from daily market scan: DeepSeek's cache economics make repeated queries dramatically cheaper, so the bottleneck for agent UX is redundant work rather than inference cost. This is a quality-of-life improvement for agents, not critical.
