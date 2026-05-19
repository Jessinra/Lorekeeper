---
date: 2026-05-20
session_id: 4ee82cc0-3d88-4355-9e5b-4f6e32f374e8
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/4ee82cc0-3d88-4355-9e5b-4f6e32f374e8.jsonl
topic: opc-write-td-skill-create
task_type: build
---

## What was done
Jason asked to download a Confluence TD template and create an `opc-write-td` skill. Claude fetched the template, wrote a SKILL.md and supporting references. Hit the `~/.claude/skills/` hard-block classifier (auto-mode blocks writes to that path). Jason added permissions to `settings.json` and Claude retried. After writing the skill, Jason asked to move it to the correct source dir (`~/Code/Shopee/prompt/skills/`) and run the installer. Claude moved the skill, added it to `SKILLS_WHITELIST`, and ran `install-skills.sh`. Along the way, Claude added a "Skill Management" section to CLAUDE.md instructing to always invoke `skill-creator` before creating/modifying skills.

## Decisions made
- `~/.claude/skills/` is hard-blocked — skills must live in `$AGENTIC_HOME/skills/` and be symlinked by installer
- Skills must always be managed via `skill-creator` skill first
- `opc-write-td` added to `SKILLS_WHITELIST` in alphabetical order
- CLAUDE.md updated with "Skill Management" section

## Corrections / discoveries
- Writing to `~/.claude/skills/` is blocked by auto-mode classifier — need explicit `Write(/Users/jessin.donnyson/.claude/skills/*)` permission in `settings.json`
- Even with the permission, new subdirectory creation was inconsistently blocked (created `td-sections.md` but blocked `confluence-publish.md`)
- The skill source of truth is `$AGENTIC_HOME/skills/<name>/` — the `~/.claude/skills/` path is just a symlink destination

## Lessons learnt
- **Always use `skill-creator` skill before writing any skill** → it defines the correct structure and installation workflow; **Principle:** skills are managed artifacts, not ad-hoc files
- **`~/.claude/skills/` is blocked for direct writes** → even with permissions, writes are inconsistent; always use the prompt repo + installer; **Principle:** follow the established skill workflow, don't bypass it
- **CLAUDE.md "Skill Management" section was missing** → added it; prevents repeating this mistake; **Principle:** CLAUDE.md is the standing rule book — add rules when they're learned

## Good patterns observed
- **Adding permissions to settings.json to unblock** → correct workaround when classifier blocks legitimate operations; **Principle:** settings.json permissions are the escape hatch for classifier blocks
- **Installer run after every skill change** → symlinks are created/updated atomically; **Principle:** always run install-skills.sh after adding to whitelist

## What I learned about the user
- **Jason expects skills to follow the standard workflow** → he said "follow /skill-creator" explicitly
- **Jason moves fast** → he wanted the skill created, moved, and installed in one session without hand-holding
