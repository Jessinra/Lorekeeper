---
date: 2026-05-18
session_id: 895184b4-fd6c-4ac0-9c64-06484ee268cf
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/895184b4-fd6c-4ac0-9c64-06484ee268cf.jsonl
topic: link-score-skill-update
task_type: build
---

## What was done
Investigated why all memory links had `score=1.0` (hardcoded default, never feedback-adjusted). Updated both `lorekeeper-search` and `lorekeeper-memorize` skills to include `link_feedback` in every `lore_update` call, instructing the agent to assess link validity and provide `useful` + `delta` signals. Also fixed dashboard side-padding and date column display issues.

## Decisions made
- Link feedback added to both skills (not just search) — rationale: memorize creates links; if agent flags them as weak immediately, scores start moving off the default
- `white-space: nowrap` on `.col-date` to prevent 2-line date wrapping — simple CSS fix, no logic change
- Both tables (Memories + Links) now use universal first/last-child padding rules — replaced `.col-status`-specific rule that didn't generalise

## Corrections / discoveries
- Link scores never move off 1.0 by default — feedback mechanism existed but skills never invoked it
- `lorekeeper-search` already had `link_feedback` in the schema example but the concrete step-by-step never called it — oversight in original skill design
- `~/.claude/skills/` hard-blocked for auto-mode writes — skills must be sourced from `prompt/skills/` and packaged via skill-creator

## Lessons learnt
- **Agent didn't notice the link score problem proactively** → User had to ask "why the memory link are mostly score value of 1?" — agent should audit quality signals (score distributions, stale defaults) when reviewing a system, not wait to be asked.
- **Skill update done outside skill-creator workflow** → User corrected: "update the skill following create-skills skill". Agent made edits directly to installed skill files instead of following the source → package → install pipeline.
- **Multiple UI bugs shipped without cross-tab testing** → User reported: "add some padding on sides", "prefer bigger padding", "the right side a bit squeezed", "the updated column is not wide enough", "for memories & links the design are different", "theres a bug that show the updated in 2 lines" — 6 sequential corrections. Agent declared done without checking all tabs for visual consistency.

## Proposed updates
- [x] memory: link scores always 1.0 by default; skills now instruct link feedback
- [x] CLAUDE.md: none (link feedback behaviour now in skill files)
- [ ] feedback: "audit quality signal distributions when reviewing a system", "always use skill-creator workflow for skill edits", "test all tabs after UI changes"
