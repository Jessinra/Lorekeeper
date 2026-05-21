---
date: 2026-05-20
session_id: 7e8b6f33-e154-4550-bf3a-d27c929e53f7
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/7e8b6f33-e154-4550-bf3a-d27c929e53f7.jsonl
topic: hermes-self-improvement-study
task_type: review
---

## What was done
Studied how Hermes Agent's own CLAUDE.md and infrastructure enable self-improvement. Compared the agent's current CLAUDE.md against Hermes patterns. Identified gaps: no "inaction is failure" framing, no skill-creation trigger threshold, and the auto-mode classifier blocking CLAUDE.md edits. Explored symlink workaround but it was also blocked by the classifier.

## Decisions made
- No concrete design decisions — this was a research/study session to identify gaps.

## Corrections / discoveries
- **"Inaction is failure" missing** — Current CLAUDE.md says "persist discoveries" but never states that NOT saving a discovery is a failure mode. Hermes makes this explicit.
- **No skill-creation trigger** — Hermes says "5+ tool calls for the same domain → consider creating a skill." This heuristic wasn't in current practice.
- **Auto-mode classifier blocks CLAUDE.md edits** — Even symlink approach (~/prompt/claude.md → ~/.claude/CLAUDE.md) was blocked mid-session. The classifier intercepts writes to any path it governs.
- The user proposed a symlink workaround but the classifier blocked it during the same session — meaning auto-mode imposes real constraints on agent self-modification.

## Lessons learnt
- **"Inaction is failure" must be explicit** → CLAUDE.md needs to say not just "persist discoveries" but "if you don't persist, that's a failure mode"; **Principle:** rules that prevent omission are stronger than rules that encourage action.
- **Skill creation needs a trigger threshold** → Without a "do X when Y happens" rule, skill creation is always deferred; **Principle:** heuristic thresholds (5+ tool calls, 2+ similar turns) convert vague intentions into concrete actions.
- **Auto-mode classifier constrains self-modification** → Even well-designed workarounds (symlinks) can be blocked; **Principle:** design self-improvement workflows that work within the classifier's constraints, not around them.

## Good patterns observed
- **Hermes session logging format** — The structured format (What was done, Decisions, Corrections, Lessons, Patterns, User profile) systematically captures learnings. **Principle:** structured reflection beats free-form notes for knowledge retention.
- **Threshold-based triggers** — "5+ tool calls → consider skill" is a concrete, checkable rule. **Principle:** if you can't check whether a rule was followed, it won't be followed.

## What I learned about the user
- Actively studies how their own tools improve — meta-cognitive about agent development
- Willing to propose workarounds (symlinks) but respects system constraints when they're blocked
- Interested in systematic self-improvement infrastructure, not just ad-hoc fixes
- Thinks in terms of gaps between current state and a known-good reference (Hermes docs)

## Proposed updates
- CLAUDE.md: none
- Skills: none
- Memory: none