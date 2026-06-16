---
id: LKPR-5
title: Add lore_get_topic_reflections for cross-session topic memory
type: feature
sprint: 3
rice_score: 12.1 # R:6 I:8 C:35% E:3w
filed_by: Hermes
github_issue: 74
filed_date: 2026-05-22
---

# [LKPR-5] Add lore_get_topic_reflections for cross-session topic memory

## Problem

`lore_reflect` captures per-session learnings but there's no higher-level view. Working on the same topic across multiple sessions produces no cumulative summary — no arc of progress, open decisions, or emerging patterns.

## Solution

New MCP tool: `lore_get_topic_reflections(topic, limit)` — pure SQL query returning all reflect entries tagged to a topic, ordered by date.

Agent-driven synthesis (zero platform LLM cost):

1. Skill instructs: "after every 5th session on the same topic, call `lore_get_topic_reflections`"
2. Agent reviews returned reflections using its own LLM
3. Agent synthesizes a topic summary and calls `lore_insert` with `memory_type: topic_summary`

## Acceptance Criteria

- [ ] `lore_get_topic_reflections(topic, limit)` returns reflect entries for a topic, ordered by date
- [ ] Pure SQL — no LLM on the platform side
- [ ] Dashboard surfaces `topic_summary` memory type distinctly in the Memories tab
- [ ] Protocol skill (LKPR-3) updated to include the "every 5th session" trigger instruction

## Affected Files

- New: `src/lorekeeper/services/topic_observer.py`
- `src/lorekeeper/models.py` — add `memory_type` field (or tag-based)
- `src/lorekeeper/handlers.py` + `server.py` — register new tool
- Dashboard — filter/display for topic summaries

## Dependencies

- LKPR-9 (session end hook) should be live first — feeds clean per-session reflect data
- `lore_reflect` must reliably tag topics

## Open Questions

- How is "topic" determined? From reflect tags? From clustering?
- Should topic summaries be auto-generated or always agent-triggered?
- How to avoid stale topic summaries when new sessions arrive?

## Notes

Long-term vision item — institutional memory, not just episodic recall. Low confidence (35%) due to unresolved topic-tagging questions. Don't build before Sprint 2 is solid.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
