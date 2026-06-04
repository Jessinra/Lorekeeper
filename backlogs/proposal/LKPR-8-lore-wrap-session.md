---
id: LKPR-8
title: Add lore_wrap_session compound tool to reduce session-end friction
type: feature
sprint: 2
rice_score: 38.0 # R:9 I:7 C:85% E:0.5w
filed_by: Hermes
github_issue: 55
filed_date: 2026-05-22
---

# [LKPR-8] Add lore_wrap_session compound tool to reduce session-end friction

## Problem

Session end requires 3 separate calls: `lore_reflect` + `lore_health` + surface any gaps. Friction adds up. Agents skip it.

## Solution

Single compound MCP tool: `lore_wrap_session(session_id?, topic?)` that runs in sequence:

1. `lore_reflect` — commit session learnings
2. `lore_health` — check store state, return fragmentation score
3. If fragmentation high → return hint: "consider calling `lore_find_nearest_pairs`"
4. Return unified summary: what was stored, health status, recommended next actions

One call. Agent gets everything it needs to decide whether to do more work or close out cleanly.

## Acceptance Criteria

- [ ] `lore_wrap_session` executes reflect + health check in a single MCP call
- [ ] Returns a structured response: `{reflected: bool, health_score: int, fragmentation: float, recommendations: list}`
- [ ] If `lore_health` (LKPR-2) is not yet implemented, wrap degrades gracefully (reflect only)
- [ ] Registered as an MCP tool in `server.py`

## Affected Files

- `src/lorekeeper/handlers.py` — new compound handler
- `src/lorekeeper/server.py` — register tool

## Dependencies

- LKPR-2 (`lore_health`) — needed for the health step; wrap can ship without it but degrades

## Required Updates

- **CLAUDE.md**: [ ] Update session-end workflow — replace 3-step reflect/insert/health with single `lore_wrap_session` call
- **README.md**: [ ] Document `lore_wrap_session` in MCP tools list
- **Skills**: [ ] Update `reflect` skill and `lorekeeper-pm` skill to call `lore_wrap_session` instead of individual reflect/insert/health
- **Backlog**: [ ] N/A — LKPR-2 dependency already noted

## Open Questions

_None_

## Notes

Small effort, high adoption impact. Reduces session-end overhead from 3 calls to 1. Fits the plug & play north star directly.
