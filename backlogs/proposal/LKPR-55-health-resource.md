---
id: LKPR-55
title: MCP Health Resource
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-01
---

# [LKPR-55] MCP Health Resource

## Problem

When Lorekeeper is unavailable (DB locked, Chroma failure, migration running), agents discover it by making a tool call and getting a cryptic traceback. That's a wasted call plus wasted context. As more agents use the same server (Akane + Bella + Copilot), a single health signal prevents N×multiple useless retries before agents fall back gracefully.

## Solution

Expose a static MCP **resource** at `lorekeeper://health` returning:
```json
{"status": "ok", "uptime_seconds": 3600, "memory_count": 142, "vector_store": "lancedb"}
```

A resource (not a tool) is cheaper — no invocation flow, agents can probe at startup. If `status != "ok"`, agents skip Lorekeeper calls and fall back gracefully.

## Acceptance Criteria

- [ ] MCP server exposes `lorekeeper://health` as a readable resource
- [ ] Response includes: `status` (ok/degraded), `uptime_seconds`, `memory_count`, `vector_store` name
- [ ] `status: degraded` if SQLite/vector store ping fails; `status: ok` otherwise
- [ ] Resource is read-only, no side effects
- [ ] Tested: server starts → `read_resource("lorekeeper://health")` returns valid JSON

## Affected Files

**Backend:**

- `src/lorekeeper/server.py` — register `lorekeeper://health` resource handler
- `src/lorekeeper/services/orchestrator.py` — expose health check method (SQLite ping + start_time)

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_

## Open Questions

- Should `memory_count` be cached or live? Live is trivial (single COUNT(*) query), prefer live for accuracy.

## Notes

XS effort — server already tracks `start_time` and has a SQLite connection. Filed from daily ideas cron output (2026-06-01). Grounded in "95% of AI pilots deliver zero ROI" — production reliability matters.

## Required Updates

- **CLAUDE.md**: [ ] Note the `lorekeeper://health` resource in architecture docs
- **README.md**: [ ] Add health resource to MCP API surface table
- **Skills**: [ ] Update `lorekeeper-search` skill to mention health check at session start
- **Backlog**: [ ] N/A
