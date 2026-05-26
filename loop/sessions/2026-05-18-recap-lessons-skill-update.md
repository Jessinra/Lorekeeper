---
date: 2026-05-18
session_id: 1b206cf7-ed15-4935-853b-f26289caf0c0
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/1b206cf7-ed15-4935-853b-f26289caf0c0.jsonl
topic: recap-lessons-skill-update
task_type: build
---

## What was done

Enhanced the `recap-sessions` skill to capture correction signals from transcripts as "Lessons learnt" entries. Added a correction-signal detection guide (table of user turn patterns), a dedicated "Lessons learnt" section to the session log format, Step 6 for storing retrospective memories in Lorekeeper, and inserted 6 retrospective memories. The section was initially called "Agent mistakes" then renamed to "Lessons learnt" for positive framing.

## Decisions made

- "Agent mistakes" → "Lessons learnt" — user requested positive framing; same content, better tone
- Retrospective memories stored as distinct entries in Lorekeeper rather than inline in factual memories — keeps them queryable and additive over time
- Correction signal detection guide added as a table in the skill — explicit patterns are more reliable than asking the agent to infer intent

## Corrections / discoveries

- The skill install pipeline is: edit source → `skill-creator` package → install to `~/.claude/skills/` — skipping any step leaves the skill out of sync
- `lore_update` only handles feedback scores (useful/confidence), not title renames — existing memories retain their original titles

## Lessons learnt

- **Committed but not installed** → agent reported "done" after committing the skill source, but the installed copy in `~/.claude/skills/` was stale. User had to ask "have you committed changes to skills dir, and run the install skill?". Next time: always run the full source → package → install pipeline before reporting completion for any skill change.
- **Negative framing in naming** → named the section "Agent mistakes" without checking user preference on framing. User redirected to "Lessons learnt". Next time: default to constructive/positive framing for retrospective sections.

## Proposed updates

- [ ] CLAUDE.md: none
- [ ] memory: insert retrospective about install pipeline discipline (covered below in Step 6 update)
- [ ] feedback: skill install pipeline rule already stored as Lorekeeper memory in this session
