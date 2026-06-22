---
id: LKPR-74
title: Observation type system with semantic icons for search output
type: feature
status: S:ready
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-08
github_issue: 168
---

# [LKPR-74] Observation type system with semantic icons for search output

## Problem

`lore_insert` has a `category` field but it's not surfaced meaningfully in agent-facing output. Search results in `format='title'` are undifferentiated — the agent has no visual or semantic cue to distinguish a critical gotcha from a routine code change. This forces the agent to either fetch everything (wasteful) or guess relevance from the title alone (error-prone).

claude-mem uses an observation type system with emoji icons (🔴 gotcha, 🟡 problem-solution, 🔵 how-it-works, 🟤 decision, ⚖️ trade-off, 🟣 discovery, 🟢 what-changed, 🟠 why-it-exists, 🎯 session-request). The legend is auto-injected at session start. Agents learn that 🔴 items are worth fetching even when the budget is tight.

## Solution

1. Add a mandatory `memory_type` field to `lore_insert` with a fixed enum:

   - `gotcha` (🔴) — critical edge case, pitfall, bug
   - `problem-solution` (🟡) — bug fix or workaround
   - `how-it-works` (🔵) — technical explanation, architecture
   - `decision` (🟤) — architecture or product decision
   - `trade-off` (⚖️) — deliberate compromise
   - `discovery` (🟣) — learning or insight
   - `what-changed` (🟢) — code/architecture change
   - `why-it-exists` (🟠) — design rationale
   - `session-request` (🎯) — user's original goal / session intent
   - `general` (📝) — default catch-all

2. Surface the type + icon prefix in `format='title'` output:

   ```
   | 🔴 | Critical auth token expiry | ~120 |
   ```

3. Auto-inject a type legend as part of the Lorekeeper system prompt or MCP resource

4. Support filter by type in `lore_search`: `lore_search(query=..., memory_type='gotcha')`

## Acceptance Criteria

- [ ] `lore_insert` accepts optional `memory_type` param (default: `general`)
- [ ] `memory_type` stored in memory metadata and indexed in SQLite
- [ ] `format='title'` output includes type icon prefix
- [ ] `lore_search` supports `memory_type` filter param
- [ ] Type legend available as MCP resource (auto-injectable by clients)
- [ ] Backward compatible — existing memories default to `general`
- [ ] Unit tests for type filtering, output formatting, and backward compatibility

## Affected Files

**Backend**: `models.py` (memory*type field), `schemas.py` (I/O schema), `handlers.py` (search filter), `services/search.py`
**Dashboard**: \_none*

## Dependencies

None. Independent feature.

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — no protocol changes needed
- **README.md**: [ ] Yes — document `memory_type` field and icon legend
- **Skills**: [ ] Yes — update `lorekeeper-search` and `lorekeeper-memorize` skills to use types
- **Backlog**: [ ] N/A

## Notes

The type system is low effort (just a string field + enum validation) but high signal value — it directly helps agents prioritize what to fetch. The same icons are useful for both AI and human consumers (web viewer, debugging).
