---
date: 2026-05-18
session_id: 9f6f6241-d115-4879-bfb7-59dd2a0fb6aa
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/9f6f6241-d115-4879-bfb7-59dd2a0fb6aa.jsonl
topic: skills-comparison
task_type: review
---

## What was done

Compared lorekeeper skills in `assets/skills/` (repo copy) vs `../prompt/skills/` (global install location). Found `lorekeeper-memorize` was identical; `lorekeeper-search` had a minor difference in the example query (OPC-specific vs generic). Clarified difference between `settings.json` (committed) and `settings.local.json` (gitignored, machine-local).

## Decisions made

- `assets/skills/` is the canonical source; global install is a copy

## Corrections / discoveries

- `settings.json` vs `settings.local.json` distinction: committed hooks go in `settings.json`, personal/machine-specific overrides in `settings.local.json`

## Lessons learnt

- none noted

## Proposed updates

- [ ] CLAUDE.md: none
- [ ] memory: none
- [ ] feedback: none
