---
id: LKPR-33
title: Smart setup — auto-detect Hermes, Claude Code, Cursor and inject Lorekeeper
type: feature
status: proposal
priority: medium
sprint: ~
rice_score: 40.0  # R:8 I:9 C:80% E:1w (reduced scope, merged LKPR-7)
filed_by: Jason → Akane
filed_date: 2026-05-25
absorbed: LKPR-7
---

# [LKPR-33] Smart setup — auto-detect agents, inject prompt/skills/MCP in one run

## Problem

Current `setup.sh` only installs deps and registers MCP for Hermes. A new Lorekeeper user (or existing user on a new machine) must manually:
- Figure out where each agent's config lives
- Manually add Lorekeeper to each agent's MCP server list
- Manually inject Lorekeeper instructions into each agent's prompt/soul file
- Manually install skills into each agent's skills directory
- Repeat for every Hermes sub-profile

This is the #1 onboarding friction for distribution. Users won't bother with a 15-step manual setup.

## Scope

**Target agents:** Hermes (main + all profiles), Claude Code, Cursor
**Not in scope:** Claude Desktop, Continue.dev, Windsurf, generic — no plans to add unless triggered

## Solution

Extend `scripts/setup.sh` to auto-detect every configured agent and configure each one:

### 1. Scanning phase (no LLM — pure filesystem + filename matching)

Scan these directories:

| Agent | Config dir | Prompt file | MCP config | Skills dir |
|---|---|---|---|---|
| **Hermes (main)** | `~/.hermes/` | `soul.md` | `config.yaml` (mcp_servers) | `skills/` |
| **Hermes (profiles)** | `~/.hermes/profiles/<name>/` | `soul.md` | `config.yaml` | `skills/` |
| **Claude Code** | project roots with `CLAUDE.md` | `CLAUDE.md` | `~/.claude/settings.json` | — |
| **Cursor** | `~/.cursor/` + project roots | `.cursorrules` | `mcp.json` | — |

Also scan for loose markdown files matching these patterns: `*CLAUDE*`, `*CURSOR*` in common project roots.

### 2. Interactive phase

Print found agents and ask:

```
Found 3 agents:
  ☑ Hermes (main)            — ~/.hermes/
  ☑ Hermes (profile: bella)  — ~/.hermes/profiles/bella/
  ☑ Cursor                   — ~/.cursor/

Configure these? [Y/n]
```

Pre-tick all detected. If user says n, exit cleanly.
No `--dry-run`, `--undo`, `--non-interactive` flags — keep it simple.

### 3. MCP injection

For each selected agent, check if `lorekeeper` already exists in the MCP config:

- **Hermes:** YAML under `mcp_servers` in `config.yaml`. Entry:
  ```yaml
  lorekeeper:
    command: uv
    args: [run, --directory, <REPO_DIR>, lorekeeper]
  ```
- **Claude Code:** JSON under `mcpServers` in `~/.claude/settings.json`. Same structure.
- **Cursor:** JSON under `mcpServers` in `~/.cursor/mcp.json`. Same structure.

If already exists → skip, log "Already configured".
If missing → append.

### 4. Prompt injection

For each selected agent:
1. Check if the prompt file already contains a `## Lorekeeper` header
2. If yes → skip, log "Already injected"
3. If no → append at end of file inside a `## Lorekeeper` section with a version stamp:

```markdown
## Lorekeeper

_Managed by setup.sh — do not edit manually_

...
```

The prompt content comes from `scripts/prompts/lorekeeper-agent-prompt.md` (new file — single source of truth).

### 5. Skills installation

For Hermes profiles (main + sub-profiles):
- Symlink or copy repo skills into each agent's `skills/` directory

For Claude Code / Cursor:
- Skip with note: "Agent type doesn't support external skills"

### 6. Post-setup summary

Print a table:

```
Agent              Prompt    MCP       Skills    Status
──────────────────────────────────────────────────────
Hermes (main)      ✓ added   ✓ added   ✓ synced  Ready
Hermes (bella)     ✓ skip    ✓ added   ✓ synced  Ready
Cursor             ✓ added   ✓ added   — n/a     Restart Cursor
```

Last line: "Restart each agent to load Lorekeeper."

### 7. Idempotency

- Version-stamped injections — re-run detects existing entries and skips
- Never duplicates — always checks existence before injecting
- Safe to re-run

## Acceptance Criteria

- [ ] `scripts/setup.sh` scans for Hermes (main + profiles), Claude Code, Cursor
- [ ] Prompt injection uses `## Lorekeeper` header check — skips if exists, appends if missing
- [ ] Injected sections carry a version stamp
- [ ] MCP injection works for JSON (Claude Code, Cursor) and YAML (Hermes) configs
- [ ] Skills symlinked into each Hermes profile's skills directory
- [ ] Prompt text lives in a single source file: `scripts/prompts/lorekeeper-agent-prompt.md`
- [ ] Existing Hermes-only setup flow still works unchanged (backward compat)
- [ ] Post-setup summary table printed
- [ ] Final instruction: "Restart each agent to activate"
- [ ] No LLM calls in any part of the scan or injection

## Affected Files

- `scripts/setup.sh` — extended with agent detection + injection logic
- `scripts/prompts/lorekeeper-agent-prompt.md` (new) — single source prompt text
- `README.md` — update setup instructions

## Dependencies

_None_ — self-contained.

## Required Updates

- **CLAUDE.md**: [ ] Document new setup flow
- **README.md**: [ ] Rewrite setup section with agent auto-detection
- **Skills**: [ ] `lorekeeper-dev` — update setup verification steps
- **Backlog**: [x] LKPR-7 absorbed into this ticket

## Notes

Merged from LKPR-7 (extend setup.sh) + LKPR-33 (full smart setup). Reduced scope from the original LKPR-33 which targeted 7 agents — now just Hermes, Claude Code, Cursor. No CLI flags kept for minimal surface area.

Design rationale:
- Pure bash — runs before `uv sync`, no Python dependency
- No LLM — filename matching only, zero runtime cost
- Version stamping is the key to idempotency
- Prompt text in its own file so it's the single source of truth