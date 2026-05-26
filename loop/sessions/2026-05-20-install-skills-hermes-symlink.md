---
date: 2026-05-20
session_id: 20260520_182103_86367165
transcript: /Users/jessin.donnyson/.hermes/sessions/20260520_182103_86367165.jsonl
topic: install-skills-hermes-symlink
task_type: build
---

## What was done

Jason asked to update `install-skills.sh` to also symlink skills into `~/.hermes/skills/` in addition to `~/.claude/skills/`. Claude refactored the script into an `install_to_dest()` function and ran it for both destinations. Updated CLAUDE.md to mention both destinations. Verified 28 skills linked.

## Decisions made

- Skills must be symlinked to both `~/.claude/skills/` AND `~/.hermes/skills/`
- `install-skills.sh` refactored with `install_to_dest()` function to avoid duplication

## Corrections / discoveries

- Prior to this change, Hermes couldn't use any skills from the prompt repo
- CLAUDE.md "create a new skill" workflow only mentioned `~/.claude/skills/` — now updated

## Lessons learnt

- **Hermes skills need symlinks too** → when adding Hermes as a second agent, its skills directory must be kept in sync; **Principle:** the installer must cover all agent destinations

## Good patterns observed

- **Refactor install_to_dest() function** → DRY when running the same install against multiple destinations; **Principle:** parameterize repetitive shell operations into functions
