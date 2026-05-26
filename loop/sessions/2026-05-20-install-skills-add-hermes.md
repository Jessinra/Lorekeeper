---
date: 2026-05-20
session_id: 20260520_182103_86367165
transcript: /Users/jessin.donnyson/.hermes/sessions/20260520_182103_86367165.jsonl
topic: install-skills-add-hermes
task_type: build
---

## What was done

User asked to update `install-skills.sh` to also symlink skills into the `~/.hermes/skills/` directory (in addition to the existing `~/.claude/skills/` destination). Refactored the script to use an `install_to_dest()` function that can be called with either destination path. The script now runs against both `~/.claude/skills/` and `~/.hermes/skills/`. Updated CLAUDE.md workflow section to mention Hermes alongside Claude. Tested the script — 28 skills were successfully linked to both destinations.

## Decisions made

- Keep a single install-skills.sh that handles both destinations via a parameterised function — avoids duplicating the install logic.
- Symlink both directions: skills from the prompt repo go to both `~/.claude/skills/` and `~/.hermes/skills/`.
- Updated CLAUDE.md to document the Hermes skill installation workflow.

## Corrections / discoveries

- The original `install-skills.sh` only deployed skills to Claude's directory — Hermes skills were either missing or manually copied.
- 28 skills were linked successfully to both destinations, confirming the refactored script works.
- The prompt repo skills directory is the source of truth — both Claude and Hermes receive symlinks from it.

## Lessons learnt

- Using a parameterised function avoids code duplication when targeting multiple installation destinations.
- One script can serve both agents — no need for separate install scripts per agent.
- Symlinks keep the source of truth in the git-managed prompt repo while making skills available at runtime paths.

## Good patterns observed

- The original script was well-structured enough that refactoring into a function was straightforward.
- Tested the script immediately (28 skills linked) — verification prevents silent failures.

## What I learned about the user

- The user wants Hermes and Claude to have parity in tooling — both should get skills installed through the same mechanism.
- The user values a single source of truth for skills (the prompt repo) with distribution to multiple agents.

## Proposed updates

- CLAUDE.md: Updated workflow section to mention Hermes skill installation
- Skills: none
- Memory: none
