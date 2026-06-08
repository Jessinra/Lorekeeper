---
id: LKPR-75
title: Agent-agnostic session auto-capture via MCP tools
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-08
github_issue: 169
---

# [LKPR-75] Agent-agnostic session auto-capture via MCP tools

## Problem

Currently Lorekeeper requires explicit `lore_insert` / `lore_remember` calls — the agent must remember to save. In practice, a lot of potentially useful context is lost between sessions because nobody explicitly triggered a save. claude-mem, Littlebird, and other competitors use automatic capture — but they achieve it by hooking into specific agent internals (Claude Code plugins, desktop screen capture).

Lorekeeper's value proposition is being **universal** — one MCP server works with every agent (Claude Code, Hermes, Cursor, Codex, Gemini, Copilot, etc). We can't hook into any specific agent's internals without breaking that promise. But we can provide standard MCP tools that **any** agent can call, and a companion wrapper that makes it trivial.

## Solution

Two-layer approach, both MCP-native:

### A. `lore_session` MCP tools (core)

Add two MCP tools that agents call at session boundaries:

- **`lore_start_session`** — Called at session start. Options:

  - `query`: optional search string to auto-inject relevant context
  - `goal`: optional description of what the user wants to accomplish
  - Returns: session ID + auto-injected context summary

- **`lore_end_session`** — Called at session end. Accepts structured session data:
  - `session_id`: returned by `lore_start_session`
  - `goal`: what was attempted
  - `outcomes`: what succeeded/failed (array of strings)
  - `decisions`: key decisions made (array of strings)
  - `files_changed`: files touched (array of paths)
  - `gotchas`: issues discovered (array of strings)
  - `type`: optional `memory_type` filter for auto-categorization
  - Returns: confirmation + inserted memory IDs

The `lore_end_session` tool auto-creates multiple memories with appropriate types:

- One `session-request` memory for the goal
- Multiple `decision`, `what-changed`, `gotcha` memories for outcomes
- Links them together as a session cluster

### B. Companion CLI wrapper (optional, for immediate use)

A lightweight shell script / Python script that any agent's init system can call:

```bash
# In agent's startup script
lore start-session --goal "$TASK_DESCRIPTION"

# In agent's teardown
lore end-session --session-id "$SID" --goal "..." --outcomes "..."
```

Zero dependencies beyond `curl` / `python3`. Works identically whether the agent is Claude Code, Hermes, Codex, or any other MCP client. Instructions go in README with copy-paste configs for each agent type.

### Why not Hermes-specific hooks?

Hermes-specific hooks would work today but violate §4.4 of the positioning manifesto: "Never optimize for one agent at the expense of others. The protocol (MCP) is the abstraction." MCP-native auto-capture means every agent benefits — no agent is special.

## Acceptance Criteria

- [ ] `lore_start_session` MCP tool registered — accepts goal, query, returns session_id
- [ ] `lore_end_session` MCP tool registered — accepts structured session data, auto-creates memories
- [ ] Session memories are linked together (via `lore_links`)
- [ ] Companion CLI script works with any agent via shell
- [ ] README documents copy-paste config for Claude Code, Hermes, Cursor, Codex
- [ ] Privacy: `<private>` tags in any string field are stripped before storage
- [ ] Short sessions (< 2 outcomes) are auto-skipped
- [ ] Opt-in by default (agent must call the tools)

## Affected Files

**Backend**: `handlers.py` (new tools), `schemas.py` (I/O schemas), `models.py` (session cluster model)
**Dashboard**: _none_
**Scripts**: new `scripts/lore-session.sh` or `scripts/lore-session.py`

## Dependencies

- LKPR-74 (type system) — auto-captured memories benefit from proper `memory_type` categories
- LKPR-8 (lore_wrap_session) — may overlap; consolidate if both are accepted

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — MCP tools are self-documenting via tool descriptions
- **README.md**: [ ] Yes — document session tools + per-agent copy-paste configs
- **Skills**: [ ] Yes — update `lorekeeper-protocol` skill to include session workflow
- **Backlog**: [ ] Yes — LKPR-8 (lore_wrap_session) may become redundant

## Open Questions

- Should `lore_start_session` auto-inject context into the prompt, or return it for the agent to decide? Auto-inject is smoother. Let the agent choose is safer.
- How to handle concurrent sessions? (User running two agents talking to one Lorekeeper.) Session IDs must be unique per client.

## Notes

Rewritten from original Hermes-centric framing per Jason's direction: Lorekeeper's value is being agent-agnostic. Auto-capture must work for ANY MCP client, not just Hermes. claude-mem's auto-capture is their strength, but their hook-based approach ties them to Claude Code — they can't follow users who switch agents. Lorekeeper's MCP-native session tools let users bring their memory anywhere.
