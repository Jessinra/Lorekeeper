---
date: 2026-05-18
session_id: 3a4b9c3a-189f-4bcf-860a-a499d46b4ec7
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/3a4b9c3a-189f-4bcf-860a-a499d46b4ec7.jsonl
topic: python-review-skill
task_type: build
---

## What was done

Created the `python-review` skill using `skill-creator` to codify a 10-category Python code review checklist (style, naming, SRP, immutability, Pythonic patterns, input sanitisation, DRY, security, pre-release hygiene). Deployed it, then immediately ran it on the lorekeeper changes via a spawned review agent.

## Decisions made

- JetBrains Qodana checklist used as primary source — 10 structured categories vs. Microsoft's tooling-focused prose
- Skill packaged in `prompt/skills/` repo (not `~/.claude/skills/` directly) so it's version-controlled and portable

## Corrections / discoveries

- Existing `/review` skill already works on Python (not Go-specific) — user assumed it was Go-only
- python-review agent found: `_all_memories()` accessed from outside class in server.py, missing return type on `update_memory` handler

## Proposed updates

- [x] memory: python-review skill created; `/review` skill is language-agnostic
- [ ] CLAUDE.md: none
