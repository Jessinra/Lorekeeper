---
date: 2026-05-18
session_id: 4c7adb75-c81a-49d6-8da6-5fea8f529293
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/4c7adb75-c81a-49d6-8da6-5fea8f529293.jsonl
topic: v1-migration-setup-script
task_type: debug
---

## What was done
Debugged dashboard not showing new memories: root cause was `lore_insert` writes going to v1 (Node.js, `memories.json`) while dashboard reads v2 (Python, `~/.lorekeeper/lorekeeper.db`). Ran migration (16 new memories + 308 links), removed `lorekeeper_old` from `~/.claude/settings.json`, fixed a Chroma index inconsistency caused by migration + dashboard both holding Chroma open simultaneously. Then created `scripts/setup.sh`, moved skills into `assets/skills/` in the repo, and cleaned personal references for public distribution.

## Decisions made
- Remove `lorekeeper_old` MCP entry entirely — user manually edited settings.json because the agent was blocked by auto-classifier
- Put skills in `assets/skills/` so they ship with the repo and `setup.sh` can install them

## Corrections / discoveries
- **Chroma "single-instance only" constraint is real**: running migration while the dashboard server holds Chroma open causes `chromadb.errors.InternalError: Error finding id` — index gets out of sync
- The auto-classifier blocked the agent from editing `~/.claude/settings.json` directly (classified as self-modification), requiring the user to make the edit manually

## Lessons learnt
- **Auto-classifier blocks settings.json edits** → when a settings.json change is required, give the user the exact diff to apply rather than trying to write it yourself — don't attempt the edit and fail
- **Migration must run with dashboard stopped** → always warn the user to stop the dashboard server before running any Chroma migration or import

## Proposed updates
- [ ] CLAUDE.md: add note that settings.json edits require user action
- [ ] memory: insert Chroma single-instance constraint and migration safety requirement
- [ ] feedback: store both lessons above
