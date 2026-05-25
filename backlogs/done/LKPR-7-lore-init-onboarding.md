---
id: LKPR-7
title: Extend setup.sh for one-shot lorekeeper onboarding
type: feature
status: cancelled
priority: medium
sprint: 2
rice_score: 216.0  # Revised: R:9 I:8 C:90% E:0.3w — extended setup.sh only, no new MCP tool
filed_by: Hermes
filed_date: 2026-05-22
closed_date: 2026-05-27
absorbed_into: LKPR-33
---

# [LKPR-7] Extend setup.sh for one-shot lorekeeper onboarding

## Problem
First-time agent setup is manual. A new agent needs MCP config registered, the protocol skill installed, and CLAUDE.md/SOUL.md updated — but `scripts/setup.sh` only handles repo deps and git hooks. No auto-setup for the agent itself.

## Solution
Extend the existing `scripts/setup.sh` to also:
- Register Lorekeeper as an MCP server in the agent's config
- Copy `lorekeeper-protocol` skill to the agent's skills dir
- Inject lorekeeper usage block into CLAUDE.md / SOUL.md

**No new MCP tools.** Zero new API surface. Just a smarter setup script.

## Acceptance Criteria
- [ ] `scripts/setup.sh` registers Lorekeeper as MCP server in agent config (Hermes + Claude Code + Cursor paths)
- [ ] `scripts/setup.sh` copies `lorekeeper-protocol` skill to agent skills dir
- [ ] `scripts/setup.sh` injects lorekeeper block (load protocol skill on start) into CLAUDE.md / SOUL.md
- [ ] `scripts/setup.sh` is idempotent — re-running doesn't duplicate entries
- [ ] `README.md` updated with "Getting Started in 5 minutes" section
- [ ] Full end-to-end run under 5 minutes

## Affected Files
- `scripts/setup.sh` — extended with agent onboarding steps
- `skills/lorekeeper-protocol.md` — already exists (from LKPR-3), just needs copying
- `README.md` — quick-start section

## Dependencies
- LKPR-3 (protocol skill) — ✅ done, shipped in sprint 1

## Design Decisions
- **No new MCP tool.** Principle: keep MCP surface minimal. A well-configured agent naturally uses existing tools (lore_search on start, lore_reflect on end) — no welcome-packet tool needed.
- **Extend setup.sh, don't create setup_agent.sh.** One script repo is simpler than two.
- **Idempotent.** Re-running setup.sh is safe.

## Open Questions
_None_

## Notes
The setup script idea came directly from Jason — inject into SOUL.md/CLAUDE.md/skills dir automatically. "Zero to working in 5 minutes" is the target.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention