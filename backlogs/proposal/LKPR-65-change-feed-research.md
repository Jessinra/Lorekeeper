---
id: LKPR-65
title: Research lore_change_feed — memory change tracking for agent session resumes
type: research
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-06-05
github_issue: 152
---

# [LKPR-65] Research lore_change_feed — memory change tracking for agent session resumes

## Problem

An agent writes memories in session A, then session B starts later. The agent has no idea what happened between sessions — it re-runs the same searches, misses that another agent updated a key fact, or accidentally duplicates work. Memory feels static, not alive.

**Status: Use case validity is NOT confirmed.** Filed from a brainstorm. Need to research whether this is a real problem agents face, and whether a change-feed tool is the right solution.

## Solution

Research the goals and use case:

1. What pain / gain does memory change tracking actually address?
2. Are there existing patterns agents use to handle cross-session awareness?
3. Is `lore_change_feed(since_timestamp)` the right interface, or should it be something simpler?
4. Would agents actually use this in practice?

## Acceptance Criteria

- [ ] Research complete: documented what problem this solves, for whom, and how urgently
- [ ] Decision made: file this properly (as feature, with spec) or defer/cancel
- [ ] If validated: draft a concrete spec with interface design

## Affected Files

**Backend:**

- `_none_` until research is done and a feature ticket is filed

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] Depends on research outcome — may file a follow-up feature ticket or cancel

## Open Questions

1. Do any existing agents (Claude Code, Codex, etc.) have native patterns for cross-session memory awareness?
2. How would an agent discover and call `lore_change_feed` on resume? Would it need prompt engineering?
3. Is the simpler alternative (agent just re-searches) actually a problem?
4. What would a minimal viable version look like? (e.g. just expose `updated_at` in search results instead of a new tool)

## Notes

Filed from lorekeeper-daily-ideas (2026-06-05). Original idea: a `lore_change_feed(since_timestamp)` tool returning `{id, title, action: created|updated, timestamp}` for each memory change since a cursor. Proposed as P2, but Jason said P3 — need more research on whether this is a valid use case. Set to P3 pending research.
