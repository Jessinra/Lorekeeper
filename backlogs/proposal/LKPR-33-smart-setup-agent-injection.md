---
id: LKPR-33
title: Smart setup — auto-detect agents, inject prompt/skills/MCP in one run
type: feature
status: in-progress
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
|-------|-----------|-------------|------------|------------|
| **Hermes (main)** | `~/.hermes/` | `soul.md` | `config.yaml` (mcp_servers) | `skills/` |
| **Hermes (profiles)** | `~/.hermes/profiles/<name>/` | `soul.md` | `config.yaml` | `skills/` |
| **Claude Code** | project roots with `CLAUDE.md` | `CLAUDE.md` | `~/.claude/settings.json` | `~/.claude/skills/` |
| **Cursor** | `~/.cursor/` + project roots | `.cursorrules` + `AGENTS.md` | `mcp.json` | `~/.cursor/skills/` |

Also scan for loose markdown files matching these patterns: `*CLAUDE*`, `*CURSOR*`, `*AGENTS*` in common project roots.

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

### 3. Version stamp (single source of truth)

The version stamp is the critical mechanism for idempotency and clean overwrites.

**Source:** `scripts/prompts/lorekeeper-agent-prompt.md` frontmatter:

```yaml
---
version: v2.0.0
---
```

Bumped manually in the prompt file when content changes meaningfully. Falls back to `git describe --always --dirty --tags` if frontmatter is missing.

**Format (everywhere):** `v{MAJOR}.{MINOR}.{PATCH}` — matches pyproject.toml.

**Where the stamp lives in each target:**

| Target | Location |
|--------|----------|
| **Prompt files** (CLAUDE.md, .cursorrules, AGENTS.md, soul.md) | HTML comment in `## Lorekeeper` header: `<!-- lorekeeper: v2.0.0 -->` |
| **MCP config** (YAML for Hermes, JSON for Claude Code/Cursor) | Env var `LOREKEEPER_SETUP_VERSION` in the lorekeeper MCP entry |
| **Skills** (all dirs) | `version:` field in skill frontmatter |

### 4. MCP injection

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

No version stamp needed on MCP — MCP configs are backward-compatible and don't need re-injection on upgrades.

### 5. Prompt injection

For each selected agent:
1. Check if the prompt file already contains a `## Lorekeeper` section with a matching version stamp
2. If version matches → skip, log "Already up to date"
3. If version differs or section missing → **replace the entire `## Lorekeeper` section** cleanly

The injected section:

```markdown
## Lorekeeper
<!-- lorekeeper: v2.0.0 | managed by: setup.sh -->

...
```

The prompt content comes from `scripts/prompts/lorekeeper-agent-prompt.md` (single source of truth).

**Replacement logic:**
- Find `## Lorekeeper` header + everything until the next `## ` header or EOF
- If exists → strip it completely, then append fresh
- If doesn't exist → append at end of file

This means re-running after an upgrade cleanly replaces the old section with the new version.

### 6. Skills installation

For **all** agent types (Hermes, Claude Code, Cursor):

- Symlink or copy repo `.hermes/skills/` into each agent's skills directory
- Each skill file has a `version:` field in its frontmatter
- If target skill exists with same version → skip
- If target skill exists with different version → overwrite cleanly
- If target skill doesn't exist → install fresh

Skills dirs:

| Agent | Skills dir |
|-------|-----------|
| Hermes (main) | `~/.hermes/skills/` |
| Hermes (profiles) | `~/.hermes/profiles/<name>/skills/` |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |

**New requirement:** All Lorekeeper-managed skills must have a `version:` stamp in their YAML frontmatter that matches the source version. The setup script reads the version from the source file and compares to the installed file.

### 7. Post-setup summary

Print a table:

```
Agent              Prompt    MCP       Skills    Status
──────────────────────────────────────────────────────
Hermes (main)      ✓ added   ✓ added   ✓ synced  Ready
Hermes (bella)     ✓ skip    ✓ added   ✓ synced  Ready
Cursor             ✓ added   ✓ added   ✓ synced  Restart Cursor
```

Last line: "Restart each agent to load Lorekeeper."

### 8. Idempotency

- Version-stamped injections — re-run detects existing entries with same version and skips
- Version mismatch → overwrites cleanly (no stale content left behind)
- Safe to re-run at any time
- Never duplicates — always checks existence + version before injecting

## Version stamp format reference

Everywhere the stamp appears, it must be parseable by simple grep/awk in bash:

**In markdown prompts:**
```markdown
## Lorekeeper
<!-- lorekeeper: v2.0.0 | managed by: setup.sh -->
```

**In skill frontmatter:**
```yaml
---
id: lorekeeper-protocol
version: v2.0.0
---
```

**For bash extraction (example):**
```bash
# Extract from prompt file
grep -oP 'lorekeeper: \K\S+' "$file"
# Extract from skill frontmatter
sed -n 's/^version: //p' "$file"
```

## Verification

How to verify setup ran correctly on each agent:

### MCP connectivity (same check for all agents)

```bash
# Hermes — check lorekeeper is listed
hermes mcp list | grep lorekeeper
# or test the connection
hermes mcp test lorekeeper

# Claude Code — in a project with CLAUDE.md
# Check MCP servers in ~/.claude/settings.json
cat ~/.claude/settings.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mcpServers',{}).get('lorekeeper','Not found'))"

# Cursor — check MCP servers tab in Cursor settings,
# or check that `lorekeeper` shows up in the MCP list
```

### Prompt injection

```bash
# Check version stamp is present in each prompt file
grep 'lorekeeper:' ~/.hermes/soul.md
grep 'lorekeeper:' ~/.hermes/profiles/*/soul.md
grep 'lorekeeper:' path/to/project/CLAUDE.md
grep 'lorekeeper:' path/to/project/.cursorrules
grep 'lorekeeper:' path/to/project/AGENTS.md
```

Expected output per file: `<!-- lorekeeper: v2.0.0 | managed by: setup.sh -->`

### Skills installed

```bash
# Check skills are present with correct version
head -5 ~/.hermes/skills/lorekeeper-protocol/SKILL.md
head -5 ~/.claude/skills/lorekeeper-protocol/SKILL.md
head -5 ~/.cursor/skills/lorekeeper-protocol/SKILL.md
```

Expected: each shows `version: v2.0.0` in frontmatter.

### MCP config

```bash
# Hermes
grep -A3 'lorekeeper:' ~/.hermes/config.yaml | head -10

# Claude Code
cat ~/.claude/settings.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('mcpServers',{}).get('lorekeeper',{}),indent=2))" 2>/dev/null || echo "Not found"

# Cursor
cat ~/.cursor/mcp.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('mcpServers',{}).get('lorekeeper',{}),indent=2))" 2>/dev/null || echo "Not found"
```

Expected: valid entry with `uv run --directory <REPO_DIR> lorekeeper`.

### Version mismatch detection

To confirm overwrite behavior works:

```bash
# Simulate an older version
sed -i 's/lorekeeper: v2.0.0/lorekeeper: v1.9.0/' ~/.hermes/soul.md

# Re-run setup
bash scripts/setup.sh

# Verify it was bumped back
grep 'lorekeeper:' ~/.hermes/soul.md
# → lorekeeper: v2.0.0
```

### Smoke test (end-to-end)

```bash
# After restarting an agent, try an actual lore search
lore_search query="hello world"
# → Returns results (or empty results, but no error)
```

## Acceptance Criteria

- [ ] `scripts/setup.sh` scans for Hermes (main + profiles), Claude Code, Cursor
- [ ] Cursor gets AGENTS.md injected alongside .cursorrules
- [ ] Prompt injection finds existing `## Lorekeeper` section, compares version stamp — skips if same, replaces entirely if different
- [ ] Version stamp format: `v{M.m.m}` — single source from `scripts/prompts/lorekeeper-agent-prompt.md` frontmatter
- [ ] MCP injection works for JSON (Claude Code, Cursor) and YAML (Hermes) configs
- [ ] MCP injection is append-if-missing, no version stamp needed (backward-compatible)
- [ ] Skills symlinked into ALL agent types (Hermes, Claude Code, Cursor) — no skip
- [ ] All Lorekeeper-managed skills get `version:` frontmatter
- [ ] Skills overwritten if installed version differs from source version
- [ ] Prompt text lives in a single source file: `scripts/prompts/lorekeeper-agent-prompt.md` (with version frontmatter)
- [ ] Existing Hermes-only setup flow still works unchanged (backward compat)
- [ ] Post-setup summary table printed with per-agent status
- [ ] Final instruction: "Restart each agent to activate"
- [ ] No LLM calls in any part of the scan or injection
- [ ] All version stamps parseable by bash grep/awk

## Affected Files

- `scripts/setup.sh` — extended with agent detection + injection logic
- `scripts/prompts/lorekeeper-agent-prompt.md` (new) — single source prompt text + version in frontmatter
- `README.md` — update setup instructions
- `.hermes/skills/*` — add `version:` frontmatter to all Lorekeeper-managed skills

## Dependencies

_None_ — self-contained.

## Required Updates

- **CLAUDE.md**: [ ] Document new setup flow
- **README.md**: [ ] Rewrite setup section with agent auto-detection
- **Skills**: [ ] `lorekeeper-dev` — update setup verification steps
- **Skills**: [ ] Add `version:` frontmatter to all Lorekeeper-managed skills
- **Backlog**: [x] LKPR-7 absorbed into this ticket

## Notes

Merged from LKPR-7 (extend setup.sh) + LKPR-33 (full smart setup). Reduced scope from the original LKPR-33 which targeted 7 agents — now just Hermes, Claude Code, Cursor. No CLI flags kept for minimal surface area.

Design rationale:
- Pure bash — runs before `uv sync`, no Python dependency
- No LLM — filename matching only, zero runtime cost
- **Version stamping is the key to idempotency AND clean upgrades** — used on prompts + skills only (MCP is backward-compatible)
- Prompt text in its own file so it's the single source of truth for both content AND version
- Full-section replacement (not line-level patching) guarantees no stale content survives upgrades