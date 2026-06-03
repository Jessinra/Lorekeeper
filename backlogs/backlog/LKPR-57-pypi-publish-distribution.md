---
id: LKPR-57
title: PyPI publish — pip install lorekeeper for zero-clone onboarding
type: feature
status: S:proposal
priority: P1:high
sprint: ~
rice_score: 72.0  # R:9 I:9 C:70% E:2d
filed_by: Jason → Akane
filed_date: 2026-06-03
---

# [LKPR-57] PyPI publish — pip install lorekeeper for zero-clone onboarding

## Problem

Lorekeeper can currently only be installed from a git clone. This blocks:

- **Casual adoption** — "try it out" requires a `git clone`, not a familiar `pip install`
- **`uv tool install lorekeeper`** — the cleanest way for Hermes users to make `lorekeeper` a global command
- **setup.sh path handling** — currently hardcodes `uv run --directory <REPO_DIR>`, which breaks when Lorekeeper is pip-installed
- **Distribution story** — README says "Clone and run" or "Build a wheel" but neither is a polished distribution experience

## Solution

### Phase 1: Ship to PyPI

The project is already ready for PyPI:

- ✅ `hatchling` build backend configured
- ✅ `[project.scripts]` with `lorekeeper` and `lorekeeper-dashboard` entry points
- ✅ `src/lorekeeper/` layout
- ⬜ Need `[project.urls]`, `license`, `classifiers`, `readme`, `keywords` in `pyproject.toml`
- ⬜ Need PyPI API token (admin: Jason)
- ⬜ Need `uv publish` (or workaround if `uv publish` isn't on this version)

**Version to publish:** `v2.1.0` (bump from current `v2.0.0` — marks the distribution release).

### Phase 2: Make setup.sh pip-aware

Current setup.sh always does `uv run --directory <REPO_DIR>`. When installed via pip, the command `lorekeeper` is on PATH. setup.sh needs to detect this.

**Detection logic (bash):**

```bash
if [ -f "$REPO_DIR/pyproject.toml" ]; then
    # Running from git clone
    MCP_CMD="uv"
    MCP_ARGS="[run, --directory, $REPO_DIR, lorekeeper]"
elif command -v lorekeeper &>/dev/null; then
    # Installed via pip / uv tool install
    MCP_CMD="lorekeeper"
    MCP_ARGS="[]"
fi
```

This means:
- **Git clone users**: `uv run --directory /path/to/lorekeeper lorekeeper` — same as today
- **Pip users**: `lorekeeper` — command on PATH, no --directory needed
- **`uv tool install lorekeeper` users**: same as pip — `lorekeeper` is a global command

The env vars (`LORE_DATA_DIR`, `LOREKEEPER_SETUP_VERSION`, `LORE_NAMESPACE`) stay the same either way.

### Phase 3: Document the new paths

- **README:** Add "Quick install" at the top showing `pip install lorekeeper` and `uv tool install lorekeeper`
- **README:** Update setup section to show both paths (clone + setup.sh vs pip + setup.sh)
- **setup.sh output:** Change "Start the dashboard" to show both `lorekeeper-dashboard` (if on PATH) and `uv run --directory ... lorekeeper-dashboard`

## Acceptance Criteria

- [ ] `uv build` produces a valid wheel + sdist
- [ ] PyPI package `lorekeeper` exists with version ≥ 2.1.0
- [ ] `pip install lorekeeper` installs successfully
- [ ] `uv tool install lorekeeper` works and `lorekeeper` is on PATH
- [ ] setup.sh detects pip-installed mode and uses `lorekeeper` command directly (no `uv run --directory`)
- [ ] setup.sh still works identically for git clone users
- [ ] MCP config injected by setup.sh uses correct command+args in both modes
- [ ] README shows both install paths, with pip first

## Affected Files

- `pyproject.toml` — add `[project.urls]`, `classifiers`, `license`, `readme`, `keywords`; bump version to 2.1.0
- `scripts/setup.sh` — add pip-detection logic for MCP command; update dashboard launch message
- `README.md` — add pip install at top, dual-path setup section
- `assets/prompts/lorekeeper-agent-prompt.md` — bump `version:` to `v2.1.0`
- `.hermes/skills/*/SKILL.md` — bump `version:` to `v2.1.0` (to stay in sync)

## How to test

1. `uv build` → check `dist/` for `.whl` + `.tar.gz`
2. `pip install dist/lorekeeper-2.1.0-py3-none-any.whl` → `lorekeeper --help` works
3. Run `bash scripts/setup.sh` on a machine without git clone → detects pip mode → uses `lorekeeper` command
4. Run `bash scripts/setup.sh` on a machine with git clone → detects git mode → uses `uv run --directory`
5. Check injected MCP config has the right command in both cases (JSON for Claude/Cursor, YAML for Hermes)

## Dependencies

_None_ — self-contained.

## Required Updates

- **README.md**: [ ] Add pip install instructions at the top, dual-path setup section
- **CLAUDE.md**: [ ] Document pip-aware setup path
- **Skills**: [ ] Bump `version:` in all `.hermes/skills/*/SKILL.md` files to `v2.1.0`
- **Prompts**: [ ] Bump `version:` in `assets/prompts/lorekeeper-agent-prompt.md` to `v2.1.0`

## Notes

**Why v2.1.0 and not v2.0.1?** This is a significant distribution milestone (PyPI availability + pip install path). Deserves a minor version bump.

**Risk:** `sentence-transformers` is a heavy dependency (PyTorch, ~800MB). First-time `pip install` will take a while. Document expected install size/time in README.

**Post-release:** Once on PyPI, consider a Homebrew tap or a `curl | sh` one-liner for even faster evaluation. Defer to follow-up.