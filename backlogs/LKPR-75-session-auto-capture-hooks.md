---
id: LKPR-75
title: Session auto-capture via Hermes lifecycle hooks
type: enhancement
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-08
github_issue: 169
---

# [LKPR-75] Session auto-capture via Hermes lifecycle hooks

## Problem

Currently Lorekeeper requires explicit `lore_insert` / `lore_remember` calls — the agent must remember to save. In practice, this means a lot of potentially useful context is lost between sessions because nobody explicitly triggered a save. claude-mem, Littlebird, and every other memory product in the space uses automatic capture: the system records what happened without the user or agent doing anything.

Lorekeeper is an MCP server, not a Claude Code plugin — we can't hook into agent internals directly. But we control the **Hermes agent framework** that consumes Lorekeeper. We can build auto-capture at the Hermes layer without polluting the MCP protocol.

## Solution

Two-sided approach:

### A. Hermes-side lifecycle hooks (primary)

Build a Hermes skill / plugin that hooks into Hermes session lifecycle:

- **Session start**: Auto-call `lore_search` to inject relevant context from past sessions
- **Post-tool-use** (optional): Summarize and save notable tool results to Lorekeeper
- **Session end**: Auto-call `lore_remember` with a compact session summary (what was achieved, key decisions, files changed)
- **On error/silent failure**: Auto-call `lore_remember` with type: `gotcha` to capture the issue

Hermes already has session management infrastructure. This integration lives at the Hermes layer, keeping the MCP interface clean.

### B. `lore_session_end` convenience endpoint (secondary, optional)

Add a lightweight endpoint that accepts structured session data (goal, outcomes, files, decisions) and auto-inserts it as a batch: one `session-request` memory for the goal, multiple `decision`/`gotcha`/`what-changed` memories for outcomes. This simplifies the Hermes integration — it's one call instead of many.

## Acceptance Criteria

- [ ] Hermes skill/plugin captures session summary on end
- [ ] Summary includes: what was attempted, what succeeded, key decisions, files touched, gotchas discovered
- [ ] Saved as Lorekeeper memory with appropriate `memory_type` (decision, gotcha, what-changed)
- [ ] Session start auto-injects relevant context via `lore_search`
- [ ] `lore_session_end` endpoint (optional) accepts structured session data and batch-inserts
- [ ] All auto-captured data is reviewable and deletable by user
- [ ] Privacy: content inside `<private>` tags or marked `sensitive: true` is excluded
- [ ] Documented workflow for enabling/disabling auto-capture

## Affected Files

**Backend**: `handlers.py` (optional `lore_session_end`), `schemas.py` (batch input schema)
**Dashboard**: _none_
**Hermes**: New skill/plugin at `~/.hermes/skills/` or `plugins/`

## Dependencies

- LKPR-74 (type system) — auto-capture output benefits from having proper `memory_type` categories
- Hermes plugin/skill system — needs to support lifecycle hooks

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — protocol unchanged
- **README.md**: [ ] Yes — document auto-capture feature and Hermes integration
- **Skills**: [ ] Yes — create new Hermes skill for lifecycle hooks
- **Backlog**: [ ] N/A

## Open Questions

- Should auto-capture be opt-in or opt-out? Opt-in is safer for privacy but means it won't be on by default.
- What level of detail? Full transcript (expensive, noisy) vs one-liner summary (lossy). Recommend: ~200-500 token AI-generated summary.
- How to handle very short sessions? (User asked one question and left.) Threshold: sessions with < 3 turns are too short to summarize meaningfully — skip.

## Notes

This is the most impactful adoption from claude-mem. Their entire system is built on auto-capture via lifecycle hooks — it's not optional for them, it's the core premise. For Lorekeeper, doing it at the Hermes layer (not the MCP layer) keeps the protocol clean while giving us the same automatic behavior. If MCP ever adds lifecycle hooks natively, we can switch to the standard path.
