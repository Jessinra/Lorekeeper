---
date: 2026-05-20
session_id: 20260520_180720_618a6bf9
transcript: /Users/jessin.donnyson/.hermes/sessions/20260520_180720_618a6bf9.jsonl
topic: reflect-hermes-sessions-add
task_type: build
---

## What was done

Jason asked why /reflect wasn't covering Hermes sessions. Claude identified that the reflect skill only scanned `~/.claude/projects/**/*.jsonl`. Claude updated the `extract_transcript.py` script to handle Hermes session format (`{"role": "user", "content": "..."}` vs Claude's `{"type": "user", ...}`) and updated the SKILL.md to add `~/.hermes/sessions/*.jsonl` as a second source. Committed as `bf48cdc`.

## Decisions made

- /reflect now scans both `~/.claude/projects/*.jsonl` AND `~/.hermes/sessions/*.jsonl`
- Hermes session format differs from Claude: uses `role` key vs `type` key
- extract_transcript.py updated to handle both formats

## Corrections / discoveries

- Hermes stores sessions as `.jsonl` with `{"role": "user"/"assistant", "content": "..."}` format
- Claude Code sessions use `{"type": "user"/"assistant", ...}` format
- The two formats require separate parsing branches in extract_transcript.py

## Lessons learnt

- **Check session format differences when adding new session sources** → Hermes uses `role` key, Claude uses `type` key; **Principle:** don't assume all JSONL session formats are identical

## Good patterns observed

- **Updated script + skill in same commit** → atomic change keeps them in sync; **Principle:** script and skill doc updates should be committed together
