---
id: LKPR-77
title: `lorekeeper setup` CLI command — one-command install
type: feat
sprint: beta
priority: P1:high
rice_score: ~
filed_by: PM (Akane)
filed_date: 2026-06-09
github_issue: 172
---

# [LKPR-77] `lorekeeper setup` CLI command — one-command install

## Problem

After `pip install lorekeeper-mcp`, the user gets a running MCP server but zero onboarding. `scripts/setup.sh` (which detects agents, injects MCP config, installs prompts, and seeds memories) only exists in the git clone — it's not shipped with the pip package. A first-time pip user has to:

1. Know that MCP config exists
2. Know where their agent stores it
3. Manually edit JSON/YAML files
4. No seed prompt, no skills, no "am I set up?" feedback

This is the #1 first-run friction for the beta.

## Solution

Ship `lorekeeper setup` as a built-in CLI subcommand in the pip package. It re-packages the logic from `scripts/setup.sh` as a proper click/typer command:

### `lorekeeper setup`

Scans for installed agents and configures them:

**Agent detection (same as setup.sh):**

- `~/.hermes/config.yaml` — Hermes main
- `~/.hermes/profiles/*/config.yaml` — Hermes profiles
- `~/.claude/settings.json` — Claude Code
- `~/.cursor/mcp.json` — Cursor

**For each detected agent:**

1. Inject lorekeeper MCP server entry (command + env vars)
2. Inject the lorekeeper-agent-prompt into the agent's prompt file (soul.md, CLAUDE.md, AGENTS.md)
3. Install user-facing skills from `assets/skills/` (copies not symlinks, since pip install has no repo path)

**Seed prompt support:**

- Offer to run the seed prompt (read agent config, save first memories) as the final step
- `lorekeeper setup --seed` to auto-run it

### `lorekeeper setup --check`

Dry-run mode: show what agents would be configured without writing anything. Useful for diagnostics.

### Supporting changes

- Bundle `assets/prompts/lorekeeper-agent-prompt.md` and `assets/skills/` in the pip package (via `include` in pyproject.toml)
- Bundle package data via `[project.scripts]` is already done for `lorekeeper` and `lorekeeper-dashboard`. Add the setup command there.

## Implementation notes

- Use `argparse` (already the CLI framework) or add `click` as a lightweight dependency
- Keep it importable as `lorekeeper.cli.setup` for testing
- The JSON/YAML injection helpers from `scripts/setup.sh` are pure Python — vendor them into `lorekeeper/cli/setup_helpers.py`
- Write tests for agent detection and config injection (not for the full install flow — that's LKPR-72 QA scope)
- Platform support: macOS only for beta (covers 90%+ of installs). Linux follow-up later.

## In scope for this ticket

- [ ] `lorekeeper setup` command with agent detection + MCP injection + prompt injection
- [ ] `assets/skills/` bundled and installable from pip
- [ ] `assets/prompts/lorekeeper-agent-prompt.md` bundled and injectable
- [ ] `lorekeeper setup --check` dry-run mode
- [ ] Tests for setup helpers (agent detection, config injection)
- [ ] Package data bundled in pyproject.toml
- [ ] Works from `pip install lorekeeper-mcp` (no git clone needed)

## Out of scope

- Dashboard installation guide — that's a README update (LKPR-71)
- Auto-capture script (`lore-capture.sh`) — separate phase (LKPR-71 Phase 5)
- E2E Playwright tests — LKPR-59
- Full QA walkthrough — LKPR-72

## Dependencies

- Needs `scripts/setup.sh` logic ported into Python (already exists as Python injection helpers within the bash script)

## Required Updates

- [ ] **CLAUDE.md**: Add `lorekeeper setup` to tooling section
- [ ] **README.md**: Update install section with `lorekeeper setup` as step 2
- [ ] **docs/quickstart.md**: Update steps to include `lorekeeper setup`
- [ ] **Skills**: `lorekeeper-dev` — add setup command reference
