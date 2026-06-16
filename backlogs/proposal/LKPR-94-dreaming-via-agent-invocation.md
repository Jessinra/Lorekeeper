---
id: LKPR-94
title: Dreaming via external agent invocation — configurable command for autonomous reflection
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane (from Letta Code competitor analysis)
filed_date: 2026-06-15
github_issue: 213
---

# [LKPR-94] Dreaming via external agent invocation

## Problem

Lorekeeper has no built-in LLM. Reflection (`lore_reflect`), consolidation, dedup, and memory defrag all require an LLM call. The server can't do any of this autonomously — it needs an agent to call the tools.

For Hermes users, this is solvable via cron jobs that spawn subagents. But for non-Hermes users (Claude Code, Cursor, Codex, Copilot), there's no mechanism for autonomous memory maintenance without the user manually prompting it.

Competitors (Letta, Claude Code autoDream) solve this with server-side scheduling where they control the LLM infrastructure. Lorekeeper doesn't have that luxury.

## Proposal — Configurable external command

Ship a lightweight script (`scripts/lore-dream.sh`) that:

1. Reads `LORE_DREAMING_CMD` env var (default: `claude --print "run lore_reflect on unprocessed sessions"`)
2. Executes the command as a subprocess
3. The command runs an agent CLI that calls Lorekeeper's MCP tools

The script is designed to be placed in system cron / launchd / systemd timer. Setup is a one-time command: `lore setup-dreaming --schedule nightly --agent claude`.

Works with any CLI agent that has headless/scriptable mode:
- Claude Code: `claude --print "instruction"`
- OpenAI Codex: `codex --instruction "instruction"`
- OpenCode: `opencode --input "instruction"`

Does NOT work with Cursor (no headless mode) or pure MCP clients (no CLI agent).

## Acceptance Criteria

- [ ] `scripts/lore-dream.sh` ships with Lorekeeper, usable standalone or via cron
- [ ] `LORE_DREAMING_CMD` env var to customize the agent invocation command
- [ ] `lore setup-dreaming` CLI command to configure schedule (writes crontab / launchd plist)
- [ ] On execution: reads unreflected sessions → runs `lore_reflect` on each → identifies stale memories → runs consolidation
- [ ] Works with Claude Code and Codex out of the box
- [ ] Docs: how to configure for different CLI agents

## Why Not

This isn't a binary choice. Local dreaming (via agent invocation) and cloud dreaming are **complementary**:

- **Local dreaming** — works now, zero infra, reuses user's existing agent auth/billing
- **Cloud dreaming** — works for everyone, no CLI agent dependency, runs even when the user's machine is off

The framing should be a **tiered progression**: local dreaming for power users who want full control and no external dependency → cloud dreaming as an optional upgrade for deeper autonomy.

Ideally, both paths share the same dreaming engine (LKPR-79) — local mode calls the agent CLI, cloud mode calls an LLM API directly. The engine is the same, only the execution backend differs.

## Effort

S (~1 day). A shell script, a CLI command, and docs. Zero changes to the Lorekeeper server itself.

## Notes

This is a pragmatic solution that defers the hard problem (Lorekeeper needing its own LLM) to the user's existing agent infrastructure. It's not elegant, but it works today and costs nothing to maintain. Revisit if we ever offer a cloud dreaming service.

Originated from Letta Code competitor analysis — Letta uses server-side scheduling for sleep-time compute, which Lorekeeper can't replicate without its own LLM infrastructure.