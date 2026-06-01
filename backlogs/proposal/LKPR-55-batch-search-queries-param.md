---
id: LKPR-55
title: Batch search — queries param on lore_search
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-01
---

# [LKPR-55] Batch Search — queries param on lore_search

## Problem

Orchestrator agents spawning multiple sub-agents (Opus 4.8 Dynamic Workflows, Notion External Agents) need to hydrate each sub-agent with relevant context. Currently this requires N sequential `lore_search` calls — latency scales linearly with agent count. At 5+ sub-agents this becomes a noticeable bottleneck before any work starts.

## Solution

Add a `queries` parameter to `lore_search`: pass a list of query strings, get back a dict keyed by query.

```python
lore_search(queries=["pricing 2026", "anomaly trends", "user segments"])
# → {"pricing 2026": [...], "anomaly trends": [...], "user segments": [...]}
```

Each query runs the existing search pipeline independently. No new data access patterns — just parallelized execution of existing logic. ~40 lines.

## Acceptance Criteria

- [ ] `lore_search` accepts optional `queries` param: list of query strings
- [ ] When `queries` is provided, returns a dict mapping each query string to its result list
- [ ] Each query runs the full existing search pipeline (hybrid BM25 + vector)
- [ ] `queries` and `query` are mutually exclusive — error if both provided
- [ ] Backward compatible — existing `query` param behaviour unchanged
- [ ] `format` param applies to all queries in batch mode

## Affected Files

**Backend:**

- `src/lorekeeper/schemas.py` — add `queries` param to `LoreSearchInput`
- `src/lorekeeper/services/orchestrator.py` — fan out across queries, aggregate results dict
- `src/lorekeeper/handlers.py` — return dict vs list depending on which param used

**Dashboard (if applicable):**

- `_none_`

## Dependencies

- LKPR-49: `format` param useful in batch mode too — ideally shipped after or together

## Open Questions

- Parallelism: `asyncio.gather` or sequential? Sequential is simpler and safe for SQLite. Start sequential, optimize later if needed.
- Max queries per call? Cap at 10 to prevent abuse.

## Required Updates

- **CLAUDE.md**: [ ] Note the `queries` batch param in architecture docs
- **README.md**: [ ] Update `lore_search` docs to document `queries` param
- **Skills**: [ ] `lorekeeper-search` — document batch search pattern for orchestrators

## Notes

Filed from daily-ideas cron 2026-06-01. Grounded in Opus 4.8 Dynamic Workflows + Notion External Agents API trend — multi-agent context hydration is a growing pattern. Jason rated P3: good UX for agents, not urgent at the moment.
