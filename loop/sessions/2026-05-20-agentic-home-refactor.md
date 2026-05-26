---
date: 2026-05-20
session_id: c2f56954-dc73-473a-9266-8e3ef24a8500
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-prompt/c2f56954-dc73-473a-9266-8e3ef24a8500.jsonl
topic: agentic-home-refactor
task_type: build
---

## What was done

Jason asked to replace all hardcoded paths (`/Users/jessin.donnyson/Code/Shopee/prompt`) with the `AGENTIC_HOME` environment variable across skills and CLAUDE.md. Claude searched all affected files, updated CLAUDE.md, skill-creator, README files, and opc_code_guide. Also created a new `skill-updater` skill (lightweight alternative to skill-creator for small edits), added it to the whitelist, and ran the installer. Committed as `4baeb35`.

## Decisions made

- `AGENTIC_HOME` is the canonical env var for the prompt repo path
- `skill-updater` created for small skill edits — skips full creation workflow
- CLAUDE.md skill management section updated to prefer `skill-updater` for small changes
- 6 files updated in one commit

## Corrections / discoveries

- `install-skills.sh` already uses `CURSOR_SKILLS_DIR` internally — `AGENTIC_HOME` is the public-facing variable
- `skill-creator` SKILL.md had two places with hardcoded paths — both needed updating
- `opc_code_guide/README.md` had `cd` command and server.js path hardcoded

## Lessons learnt

- **Always search broadly for hardcoded paths before updating** → grep across all files in the prompt repo; **Principle:** hardcoded paths are a cross-cutting concern, not a single-file fix

## Good patterns observed

- **Creating skill-updater alongside the refactor** → the refactor revealed the gap; Jason's skill management needed a lightweight update path; **Principle:** build the tool you needed during this session
- **Commit all related changes atomically** → 6 files in one commit with clear message; **Principle:** atomic commits for related refactors

## What I learned about the user

- **Jason wants a clean skill management system** → he proactively drove the AGENTIC_HOME refactor and the skill-updater creation
