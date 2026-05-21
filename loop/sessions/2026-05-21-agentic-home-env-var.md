---
date: 2026-05-21
session_id: c2f56954-dc73-473a-9266-8e3ef24a8500
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-prompt/c2f56954-dc73-473a-9266-8e3ef24a8500.jsonl
topic: agentic-home-env-var
task_type: build
---

## What was done

Updated all skills and CLAUDE.md that hardcoded `/Users/jessin.donnyson/Code/Shopee/prompt/` to use `$AGENTIC_HOME` env var instead. Created `skill-updater` skill (lightweight alternative to `skill-creator` for small edits). Added `skill-updater` to SKILLS_WHITELIST. Committed as 4baeb35.

## Decisions made

- `$AGENTIC_HOME` is the canonical env var for the prompt/skills directory
- `skill-updater` is for small targeted edits; `skill-creator` for full new skills with the creation wizard
- `install-skills.sh` now symlinks to both `~/.claude/skills/` AND `~/.hermes/skills/`

## Corrections / discoveries

- (None — session was straightforward with no corrections)

## Lessons learnt

- **Use env vars for paths** — hardcoded paths break when moving between contexts. `$AGENTIC_HOME` future-proofs all skills
- **Lightweight skill-updater** exists — don't always need the full skill-creator wizard for minor edits

## Good patterns observed

- **Search and replace systematically**: Searched all skills for the hardcoded path, replaced each one consistently
- **Created a lightweight tool for a common use case**: skill-updater fills the gap between "edit manually" and "full skill-creator wizard"

## What I learned about the user

- Jason prefers systematic refactoring — find all occurrences, replace consistently, update all dependencies
- Jason appreciates having lightweight tooling for common tasks (skill-updater vs always skill-creator)

## Proposed updates

- Memory: $AGENTIC_HOME env var is the canonical path for prompt/skills directory
- Memory: skill-updater skill exists for lightweight skill edits (vs skill-creator for new skills)
