---
id: LKPR-47
title: lore playground — first-run interactive exploration mode
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 89
filed_date: 2026-05-28
---

# [LKPR-47] lore playground — first-run interactive exploration mode

## Problem

New user installs Lorekeeper, reads the README, then needs to configure an MCP host, connect an agent, and write code to call `lore_search`. There's a "I installed it, now what?" gap between setup and first "aha" moment — pure config-to-code with no dopamine hit on first run.

## Solution

A `lore playground` CLI command that starts a zero-config interactive session — terminal TUI or localhost web UI. User types a memory, saves it. Types a search query, sees hybrid results with score breakdowns. Shows the memory graph. It's the dashboard's "Explore" mode in a single-purpose, 2-second-launch tool. No config, no MCP host setup — just `pip install lorekeeper && lore playground`.

Also doubles as a debugging tool for existing users.

## Acceptance Criteria

- [ ] `lore playground` launches without any MCP host configuration
- [ ] User can save a memory and see it persisted
- [ ] User can search and see hybrid results with score breakdowns
- [ ] Works immediately after `pip install` with no additional setup

## Affected Files

**Backend:**

- `src/lorekeeper/cli/playground.py` — new CLI command entry point

**Dashboard (if applicable):**

_none_ — standalone CLI tool, not in the dashboard

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] Mention `lore playground` as a quickstart option
- **README.md**: [ ] Add "Quickstart — try it in 2 minutes" section
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- TUI vs localhost web UI? TUI has fewer dependencies (blessed/rich), web UI would reuse dashboard components.
- Should this bundle a small demo dataset on first launch to immediately demonstrate search?

## Notes

Originated from lorekeeper-daily-ideas cronjob (2026-05-28). More effort than initial estimate (M, not S) once you account for UX polish and edge cases. Needs are unclear — filed at P3. Jason noted: "high effort with lower return (unclear needs)." Worth revisiting if onboarding feedback shows this is a real gap.