---
id: LKPR-33
title: Smart setup — auto-detect agents, inject prompt/skills/MCP in one run
type: feature
status: proposal
priority: medium
sprint: ~
rice_score: 12.0  # R:8 I:9 C:50% E:3w
filed_by: Jason
filed_date: 2026-05-25
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

## Solution

Upgrade `setup.sh` to auto-detect every AI agent on the machine and offer to configure each one:

### 1. Scanning phase (no LLM — pure filesystem + filename matching)

Scan these directories:

| Agent | Config dir | Prompt file | MCP config | Skills dir |
|---|---|---|---|---|
| **Hermes (main)** | `~/.hermes/` | `soul.md` | `config.yaml` (mcp_servers) | `skills/` |
| **Hermes (profiles)** | `~/.hermes/profiles/<name>/` | `soul.md` | `config.yaml` | `skills/` |
| **Claude Desktop** | `~/.claude/` or `~/Library/Application Support/Claude/` | `CLAUDE.md` | `claude_desktop_config.json` | — |
| **Claude Code** | project roots with `CLAUDE.md` | `CLAUDE.md` | `~/.claude/settings.json` | — |
| **Cursor** | `~/.cursor/` + project roots | `.cursorrules` | `mcp.json` | — |
| **Continue.dev** | `~/.continue/` | `instructions/` | `config.json` (mcpServers) | — |
| **Windsurf** | `~/.codeium/windsurf/` | `windsurf_rules/` | `mcp_config.json` | — |
| **Generic** | any dir with `AGENTS.md`, `SOUL.md`, `SYSTEM.md` | by filename match | — | `skills/` if exists |

Also scan for loose markdown files matching these patterns: `*CLAUDE*`, `*SOUL*`, `*AGENT*`, `*SYSTEM*`, `*CURSOR*` in common agent directories and project roots.

### 2. Interactive phase

Present a checklist to the user:

```
Found 4 agents on this machine:

☑ Hermes (main)          — ~/.hermes/
☑ Hermes (profile: bella) — ~/.hermes/profiles/bella/
☑ Claude Desktop         — ~/Library/Application Support/Claude/
☑ Cursor                 — ~/.cursor/
☐ Windsurf               — ~/.codeium/windsurf/
  (not detected — add custom path)

[Proceed with selected]  [Dry run — show what would change]
```

Pre-tick based on filename relevance (agent directories, known config patterns).

### 3. Prompt injection

For each selected agent:

1. Check if the prompt file already contains a `## Lorekeeper` header
2. If yes → skip, log "Already injected (v{X.Y.Z})" — detect version tag for upgrade warnings
3. If no → append at end of file inside a `## Lorekeeper` section with a version stamp:

```markdown
## Lorekeeper

_Managed by setup.sh v2.0.0 — do not edit manually_

...
```

The prompt content comes from `scripts/prompts/lorekeeper-agent-prompt.md` (a new file — single source of truth for agent instructions).

### 4. MCP configuration

For each selected agent:

1. Read the agent's MCP config file (JSON or YAML)
2. Check if `lorekeeper` already exists under the MCP servers section
3. If yes → skip, check version compatibility, warn if outdated
4. If no → append the Lorekeeper MCP entry with:
   - Command: `uv`
   - Args: `[run, --directory, <REPO_DIR>, lorekeeper]`
   - Env: `{ LORE_DATA_DIR: <DATA_DIR> }`

Use agents' native config format:
- Hermes: YAML under `mcp_servers`
- Claude/Cursor/Continue: JSON under `mcpServers`

### 5. Skills installation

For agents with a skills directory (Hermes):
- Symlink or copy repo skills into each agent's `skills/` directory
- Respect the existing category mapping (`skill_category()`)

For agents without a skill concept (Claude, Cursor):
- Skip with a note: "Agent type doesn't support external skills"
- (Future: could auto-generate assistant config)

### 6. Post-setup summary

Print a table:

```
Agent              Prompt    MCP       Skills    Status
──────────────────────────────────────────────────────
Hermes (main)      ✓ added   ✓ added   ✓ synced  Ready
Hermes (bella)     ✓ skip    ✓ added   ✓ synced  Ready
Claude Desktop     ✓ added   ✓ added   — n/a     Restart Claude
Cursor             ✓ added   ✓ addded  — n/a     Restart Cursor
```

Last line: "Restart each agent to load Lorekeeper."

### 7. Idempotency & upgrade detection

Per-config-type version stamping:

- **Agent prompt files** (soul.md, CLAUDE.md, .cursorrules): header line `## Lorekeeper (v2.1.0)` — human-readable, easy to grep
- **MCP config** (JSON/YAML): inject version as an env variable in the Lorekeeper MCP entry:
  ```yaml
  mcp_servers:
    lorekeeper:
      env:
        LOREKEEPER_SETUP: "v2.1.0"
```
  Clean, doesn't pollute the config, reuses existing `env` block
- **Skills directory**: version file `SKILL_VERSION` or frontmatter field in SKILL.md

On re-run:
- If stamp matches current version → "Already configured (up to date)"
- If stamp < current version → "⚠️ Lorekeeper section outdated (v1.0.0 → v2.1.0) — updating..."
- If no stamp → assume legacy, update in place
- Never duplicates — always checks existence before injecting

### 8. Flags (CLI interface)

| Flag | Effect |
|---|---|
| (no flags) | Interactive prompts, user selects agents |
| `--dry-run` | Show what would change, don't touch anything |
| `--non-interactive` | Auto-select all detected agents, no user prompts |
| `--agent <name>` | Target a specific agent by name (can repeat) |
| `--agents-file <path>` | Scan a custom path for agent configs |
| `--undo` | Remove all Lorekeeper injections, MCP entries, skill symlinks |

## Acceptance Criteria

- [ ] `scripts/setup.sh` scans for all 7 agent types listed above (Hermes, Claude Desktop, Claude Code, Cursor, Continue, Windsurf, generic)
- [ ] Prompt injection uses `## Lorekeeper` header check — skips if exists, appends if missing
- [ ] Injected sections carry a version stamp for upgrade detection
- [ ] Re-run detects stale version and warns/updates
- [ ] MCP injection works for JSON (Claude, Cursor) and YAML (Hermes) configs
- [ ] `--dry-run` shows all changes without writing
- [ ] `--non-interactive` applies to all detected agents
- [ ] `--undo` strips all Lorekeeper traces
- [ ] Skills symlinked into each Hermes profile's skills directory
- [ ] Prompt text lives in a single source file: `scripts/prompts/lorekeeper-agent-prompt.md`
- [ ] Existing Hermes-only setup flow still works unchanged (backward compat)
- [ ] Post-setup summary table printed
- [ ] Final instruction: "Restart each agent to activate"
- [ ] No LLM calls in any part of the scan or injection

## Affected Files

**Scripts (new + modified):**
- `scripts/setup.sh` — major rewrite, agent scan + injection logic
- `scripts/lib/agent_scanner.sh` (new) — pure bash filesystem scanner for agent directories
- `scripts/lib/prompt_injector.sh` (new) — inject prompt sections with version stamps
- `scripts/lib/mcp_injector.sh` (new) — manage MCP entries per config format (JSON/YAML)
- `scripts/lib/skill_installer.sh` (new) — symlink skills per agent type
- `scripts/lib/utils.sh` (new) — shared helpers (color, logging, version compare)
- `scripts/prompts/lorekeeper-agent-prompt.md` (new) — single source prompt text

**Docs:**
- `README.md` — update setup instructions with new flags

## Dependencies

_None_ — self-contained. Doesn't block or depend on any other LKPR. However, the prompt content file (`lorekeeper-agent-prompt.md`) is shared — any future update to the agent prompt should update this file.

## Required Updates

- **CLAUDE.md**: [ ] Document new setup flags and agent auto-detection flow
- **README.md**: [ ] Rewrite setup section:
  - "This script will scan your machine for AI agents, then inject Lorekeeper configuration into each one"
  - List what gets changed: prompt files (soul.md, CLAUDE.md, etc.), MCP configs, skills directories
  - Show `--dry-run` before first run
  - Show `--undo` for rollback
  - Include a clear example: `bash scripts/setup.sh --dry-run` → review → `bash scripts/setup.sh`
- **Skills**: [ ] `lorekeeper-dev` — update setup verification steps; add new lib scripts to dev skill
- **Backlog**: [ ] After shipping, consider follow-up LKPR for Docker/CI setup guide using `--non-interactive`

## Open Questions

- **What about Windows/WSL?** Setup is bash-based. Should the scanner support `%APPDATA%` paths for Claude Desktop? (Defer — v1 is macOS/Linux only.)
- **What about PyPI distribution (`pip install lorekeeper`)?** The setup script assumes a git clone. When distributed via PyPI, the script paths change. Should we ship a `lorekeeper-setup` CLI command instead? (Defer — get the script right first, then wrap as CLI.)
- **Should we support `--ci` as an alias for `--non-interactive`?** (Yes, add as alias.)
- **Write detection for `~/.cursor/mcp.json`:** Cursor uses `~/.cursor/mcp.json` — but is it a flat `mcpServers` object or nested? Need to verify on real installs.
- **Continue.dev paths:** Some installs use `~/.continue/config.json`, others use platform-specific app data. Should we search both?

## Notes

Filed by Jason as a distribution enabler (#2). This is the complement to LKPR-32 (encrypted backup/restore) — LKPR-32 handles moving data out, LKPR-33 handles getting a new user running.

**Design rationale:**
- Pure bash (no Python dependency) — runs before `uv sync` completes, works on machines without Python/Lorekeeper deps
- No LLM — filename matching only, no runtime cost, no API key needed
- Version stamping is the key to idempotency — re-runs are safe and informative
- The `--undo` flag makes it feel low-risk to try — critical for user trust
- Prompt text in its own file (`scripts/prompts/`) so it's the single source of truth that agents, docs, and README all reference

**My additions:**
- `--dry-run` — user confidence builder before touching files
- `--undo` — makes experimentation safe
- `--non-interactive` — for Docker/CI/CD distribution scenarios
- Version stamping — enables upgrade detection without touching user files unnecessarily
- Per-agent type detection by config file shape (not just directory names)

**Trade-offs acknowledged:**
- Bash is less elegant than Python but has zero dependency requirements (can run before `uv sync`)
- JSON config manipulation in bash is fragile (using `jq` as a required dep) — accept `jq` as a new prerequisite
- Cross-platform path differences (macOS `~/Library` vs Linux `~/.config`) — accepted risk, first users are developers/agent users who can handle it
- Requires `jq` — accepted risk, target audience already has dev tooling
- The scanner may produce false positives (finding a `soul.md` in an unrelated project) — mitigated by pre-tick UI where user confirms