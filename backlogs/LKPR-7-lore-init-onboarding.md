---
id: LKPR-7
title: Add lore_init tool and setup script for zero-friction onboarding
type: feature
status: backlog
priority: medium
sprint: 2
rice_score: 35.0  # R:9 I:7 C:75% E:1w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-7] Add lore_init tool and setup script for zero-friction onboarding

## Problem
First-time setup is manual. A new agent has to figure out what memories to seed, which skills to load, and what the health baseline is. High barrier for new adopters.

## Solution
New MCP tool: `lore_init(agent_name, purpose)` — returns a quick-start checklist: suggested starter memories, health baseline, which skill file to load, and what to do in the first 3 sessions.

Bonus: `scripts/setup_agent.sh` that:
- Copies skill files to agent's skills directory
- Injects a lorekeeper block into SOUL.md / CLAUDE.md
- Registers MCP server in agent config
- Runs `lore_init` automatically

One script. Any agent is fully configured.

## Acceptance Criteria
- [ ] `lore_init(agent_name, purpose)` returns structured onboarding guidance with no LLM calls
- [ ] `scripts/setup_agent.sh` runs end-to-end and configures a fresh agent in <5 minutes
- [ ] Setup script handles Hermes, Claude Code, and Cursor config paths
- [ ] `README.md` updated with "Getting Started in 5 minutes" section pointing to the script

## Affected Files
- `src/lorekeeper/handlers.py` — `lore_init` handler
- New: `scripts/setup_agent.sh`
- New: `skills/lorekeeper-protocol.md` — injected by setup script (see LKPR-3)
- `README.md` — quick-start section

## Dependencies
- LKPR-3 (protocol skill) — ✅ done, shipped in sprint 1. Setup script copies it to agent skills dir.

## Open Questions
_None_

## Notes
The setup script idea came directly from Jason — inject into SOUL.md/CLAUDE.md/skills dir automatically. "Zero to working in 5 minutes" is the target.
