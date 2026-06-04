---
id: LKPR-2
title: Add lore_health and lore_stats tools for agent self-audit
type: feature
sprint: 1
rice_score: 32.4 # R:6 I:7 C:90% E:1w
filed_by: Hermes
github_issue: 62
filed_date: 2026-05-22
---

# [LKPR-2] Add lore_health and lore_stats tools for agent self-audit

## Problem

Agents have no way to self-audit the memory store. No visibility into store health, dead-weight memories, orphaned nodes, or coverage gaps.

## Solution

Two new MCP tools:

**`lore_health`** — memory store health check:

- Total memory count, avg score
- Orphaned nodes (memories with no links)
- Stale memories (not used in >30 days)
- Coverage gaps (topics with only 1 memory)
- Overall health score (0–100)

**`lore_stats`** — store analytics:

- Top topics by memory count
- Most/least used memories
- Score distribution histogram
- Memories added per week (growth rate)

## Acceptance Criteria

- [ ] `lore_health` returns a structured health report with score 0–100
- [ ] `lore_stats` returns store analytics without any LLM calls
- [ ] Both tools are exposed via MCP (`server.py`)
- [ ] Dashboard surfaces health warnings via the same API endpoint
- [ ] No LLM cost — all logic is pure SQL over existing SQLite schema

## Affected Files

- `src/lorekeeper/handlers.py` — two new handlers
- `src/lorekeeper/server.py` — register tools
- `src/lorekeeper/services/orchestrator.py` — health/stats query methods
- `src/lorekeeper/dashboard/app.py` — expose via API endpoint

## Dependencies

_None_

## Open Questions

_None_

## Notes

Mostly SQL queries over existing SQLite schema — low risk, high value. Prerequisite for LKPR-11 (sleep cycle consolidation) and LKPR-8 (lore_wrap_session).

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
