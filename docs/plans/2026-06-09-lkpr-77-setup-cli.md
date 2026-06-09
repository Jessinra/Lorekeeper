# LKPR-77: `lorekeeper setup` CLI Command — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Port `scripts/setup.sh` agent detection + config injection logic into a `lorekeeper setup` Python CLI subcommand, bundled with the pip package so it works without a git clone.

**Architecture:** New `src/lorekeeper/cli/` package with `setup_helpers.py` (pure functions: agent detection, MCP injection, prompt injection, skills install) and `setup.py` (CLI orchestrator). Assets (`assets/skills/`, `assets/prompts/`) moved to `src/lorekeeper/assets/` so they're auto-bundled in the wheel. `__main__.py` gets argparse subcommand routing while preserving backward-compat (no args → run MCP server as before).

**Tech Stack:** Python 3.11+, `argparse` (no new deps), `shutil`, standard `json`/`re`.

**Branch:** `lkpr-77-cli-setup-command`

---

## Task 1: Move assets into the package tree

**Objective:** Relocate `assets/skills/` and `assets/prompts/` to `src/lorekeeper/assets/` so hatchling auto-bundles them in the wheel without extra pyproject.toml configuration.

**Files:**

- Move: `assets/skills/` → `src/lorekeeper/assets/skills/`
- Move: `assets/prompts/` → `src/lorekeeper/assets/prompts/`
- Modify: `scripts/setup.sh` lines 7–8 — update `SKILLS_USER` and `PROMPT_FILE` vars
- Keep: `assets/*.png` at root (README images, don't touch)

**Step 1: git mv**

```bash
cd /Users/jessinra/Code/lorekeeper
mkdir -p src/lorekeeper/assets
git mv assets/skills src/lorekeeper/assets/skills
git mv assets/prompts src/lorekeeper/assets/prompts
```

**Step 2: Update setup.sh**

In `scripts/setup.sh`, change lines 7–8:

```bash
# Before:
SKILLS_USER="$REPO_DIR/assets/skills"
PROMPT_FILE="$REPO_DIR/assets/prompts/lorekeeper-agent-prompt.md"

# After:
SKILLS_USER="$REPO_DIR/src/lorekeeper/assets/skills"
PROMPT_FILE="$REPO_DIR/src/lorekeeper/assets/prompts/lorekeeper-agent-prompt.md"
```

**Step 3: Verify files are present**

```bash
ls src/lorekeeper/assets/skills/
ls src/lorekeeper/assets/prompts/
# Expected: 5 skill dirs and lorekeeper-agent-prompt.md
```

**Step 4: Run unit tests**

```bash
uv run pytest -x -q
# Expected: all green — no existing test depends on assets/ location
```

**Step 5: Commit**

```bash
git add scripts/setup.sh src/lorekeeper/assets/
git commit -m "[LKPR-77] chore: move assets into package tree for pip bundling"
```

---

## Task 2: Create `lorekeeper/cli/` package + agent detection

**Objective:** New package with `AgentType`, `DetectedAgent`, and `detect_agents()` — scans for Hermes / Claude Code / Cursor installs.

**Files:**

- Create: `src/lorekeeper/cli/__init__.py`
- Create: `src/lorekeeper/cli/setup_helpers.py` (agent detection section)
- Create: `tests/test_cli_setup.py` (failing tests first)

**Step 1: Write failing tests for agent detection**

Create `tests/test_cli_setup.py`:

```python
"""Tests for lorekeeper CLI setup helpers — agent detection and config injection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lorekeeper.cli.setup_helpers import AgentType, DetectedAgent, detect_agents


# ── Agent detection ────────────────────────────────────────────────────────────

def test_detect_hermes_main(tmp_path: Path) -> None:
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    (hermes / "config.yaml").write_text("model: test\n")
    agents = detect_agents(home=tmp_path)
    assert len(agents) == 1
    assert agents[0].type == AgentType.HERMES_MAIN
    assert agents[0].name == "Hermes (main)"
    assert agents[0].namespace == "shared"


def test_detect_hermes_profile(tmp_path: Path) -> None:
    profiles = tmp_path / ".hermes" / "profiles" / "diana"
    profiles.mkdir(parents=True)
    (profiles / "config.yaml").write_text("model: test\n")
    agents = detect_agents(home=tmp_path)
    assert any(
        a.type == AgentType.HERMES_PROFILE and a.name == "Hermes (profile: diana)"
        for a in agents
    )
    diana = next(a for a in agents if a.type == AgentType.HERMES_PROFILE)
    assert diana.namespace == "diana"


def test_detect_claude_code(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}")
    agents = detect_agents(home=tmp_path)
    assert any(a.type == AgentType.CLAUDE for a in agents)


def test_detect_cursor(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".cursor" / "mcp.json").write_text("{}")
    agents = detect_agents(home=tmp_path)
    assert any(a.type == AgentType.CURSOR for a in agents)


def test_detect_no_agents(tmp_path: Path) -> None:
    assert detect_agents(home=tmp_path) == []


def test_detect_hermes_dir_without_config(tmp_path: Path) -> None:
    (tmp_path / ".hermes").mkdir()
    agents = detect_agents(home=tmp_path)
    assert any(a.type == AgentType.HERMES_MAIN for a in agents)
```

**Step 2: Run — confirm all fail (ImportError)**

```bash
uv run pytest tests/test_cli_setup.py -x -q
# Expected: ImportError — lorekeeper.cli doesn't exist yet
```

**Step 3: Create package files**

`src/lorekeeper/cli/__init__.py`:

```python
"""Lorekeeper CLI commands."""
```

`src/lorekeeper/cli/setup_helpers.py`:

```python
"""Setup helpers — agent detection, MCP/prompt/skills injection.

All functions are pure (no side effects in check mode) and importable for testing.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

import lorekeeper

# Package root: works for both installed and editable (uv dev) installs.
_PKG_ROOT = Path(lorekeeper.__file__).parent
ASSETS_DIR = _PKG_ROOT / "assets"

SetupResult = Literal["added", "updated", "skip", "missing", "error"]


class AgentType(Enum):
    HERMES_MAIN = "hermes_main"
    HERMES_PROFILE = "hermes_profile"
    CLAUDE = "claude"
    CURSOR = "cursor"


@dataclass
class DetectedAgent:
    name: str
    type: AgentType
    dir: Path
    namespace: str  # "shared" for hermes_main/claude/cursor; profile name for hermes_profile


def detect_agents(home: Path | None = None) -> list[DetectedAgent]:
    """Scan well-known locations for installed AI agents."""
    if home is None:
        home = Path.home()
    agents: list[DetectedAgent] = []

    hermes_dir = home / ".hermes"
    if hermes_dir.is_dir():
        agents.append(DetectedAgent(
            name="Hermes (main)", type=AgentType.HERMES_MAIN,
            dir=hermes_dir, namespace="shared",
        ))
        profiles_dir = hermes_dir / "profiles"
        if profiles_dir.is_dir():
            for profile_dir in sorted(profiles_dir.iterdir()):
                if profile_dir.is_dir():
                    agents.append(DetectedAgent(
                        name=f"Hermes (profile: {profile_dir.name})",
                        type=AgentType.HERMES_PROFILE,
                        dir=profile_dir,
                        namespace=profile_dir.name,
                    ))

    claude_dir = home / ".claude"
    if claude_dir.is_dir() or (claude_dir / "settings.json").exists():
        agents.append(DetectedAgent(
            name="Claude Code", type=AgentType.CLAUDE,
            dir=claude_dir, namespace="shared",
        ))

    cursor_dir = home / ".cursor"
    if cursor_dir.is_dir() or (cursor_dir / "mcp.json").exists():
        agents.append(DetectedAgent(
            name="Cursor", type=AgentType.CURSOR,
            dir=cursor_dir, namespace="shared",
        ))

    return agents
```

**Step 4: Run tests — agent detection should pass**

```bash
uv run pytest tests/test_cli_setup.py -x -q -k "detect"
# Expected: 6 passed
```

**Step 5: Commit**

```bash
git add src/lorekeeper/cli/ tests/test_cli_setup.py
git commit -m "[LKPR-77] feat: cli package + agent detection"
```

---

## Task 3: `setup_helpers.py` — MCP injection (JSON + YAML)

**Objective:** Add helpers to inject the `lorekeeper` MCP entry into Claude/Cursor JSON configs and Hermes YAML configs.

**Files:**

- Modify: `tests/test_cli_setup.py` — add failing tests
- Modify: `src/lorekeeper/cli/setup_helpers.py` — add injection functions

**Step 1: Add failing tests** (append to `tests/test_cli_setup.py`)

```python
from lorekeeper.cli.setup_helpers import inject_mcp_json, inject_mcp_yaml


# ── MCP injection (JSON) ───────────────────────────────────────────────────────

def test_inject_mcp_json_adds_to_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "settings.json"
    cfg.write_text("{}")
    result = inject_mcp_json(cfg, data_dir=tmp_path / ".lorekeeper")
    assert result == "added"
    data = json.loads(cfg.read_text())
    assert "lorekeeper" in data["mcpServers"]
    assert data["mcpServers"]["lorekeeper"]["command"] == "lorekeeper"


def test_inject_mcp_json_skips_if_present(tmp_path: Path) -> None:
    cfg = tmp_path / "settings.json"
    cfg.write_text('{"mcpServers": {"lorekeeper": {"command": "lorekeeper"}}}')
    assert inject_mcp_json(cfg, data_dir=tmp_path / ".lorekeeper") == "skip"


def test_inject_mcp_json_missing_file(tmp_path: Path) -> None:
    assert inject_mcp_json(tmp_path / "nope.json", data_dir=tmp_path) == "missing"


def test_inject_mcp_json_creates_mcpservers_key(tmp_path: Path) -> None:
    cfg = tmp_path / "settings.json"
    cfg.write_text('{"theme": "dark"}')
    inject_mcp_json(cfg, data_dir=tmp_path / ".lorekeeper")
    data = json.loads(cfg.read_text())
    assert "mcpServers" in data and "lorekeeper" in data["mcpServers"]


# ── MCP injection (YAML) ───────────────────────────────────────────────────────

def test_inject_mcp_yaml_adds_to_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("model: claude\n")
    result = inject_mcp_yaml(cfg, data_dir=tmp_path / ".lorekeeper", namespace="shared")
    assert result == "added"
    content = cfg.read_text()
    assert "lorekeeper:" in content
    assert "mcp_servers:" in content


def test_inject_mcp_yaml_skips_if_present(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mcp_servers:\n  lorekeeper:\n    command: lorekeeper\n")
    assert inject_mcp_yaml(cfg, data_dir=tmp_path / ".lorekeeper", namespace="shared") == "skip"


def test_inject_mcp_yaml_missing_file(tmp_path: Path) -> None:
    assert inject_mcp_yaml(tmp_path / "nope.yaml", data_dir=tmp_path, namespace="shared") == "missing"


def test_inject_mcp_yaml_profile_namespace(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("model: claude\n")
    inject_mcp_yaml(cfg, data_dir=tmp_path / ".lorekeeper", namespace="diana")
    assert '"diana"' in cfg.read_text()
```

**Step 2: Append injection functions to `src/lorekeeper/cli/setup_helpers.py`**

```python
def inject_mcp_json(config_path: Path, data_dir: Path) -> SetupResult:
    """Inject lorekeeper MCP entry into a JSON config (Claude Code / Cursor).

    In pip-install mode the command is always ``lorekeeper`` (no uv run needed).
    """
    if not config_path.exists():
        return "missing"
    try:
        data: dict[str, object] = json.loads(config_path.read_text())
    except json.JSONDecodeError:
        return "error"
    mcp_servers = data.get("mcpServers", {})
    if isinstance(mcp_servers, dict) and "lorekeeper" in mcp_servers:
        return "skip"
    backup = config_path.with_suffix(".json.setup-bak")
    shutil.copy2(config_path, backup)
    try:
        if not isinstance(data.get("mcpServers"), dict):
            data["mcpServers"] = {}
        data["mcpServers"]["lorekeeper"] = {  # type: ignore[index]
            "command": "lorekeeper",
            "args": [],
            "env": {"LORE_DATA_DIR": str(data_dir)},
        }
        config_path.write_text(json.dumps(data, indent=2) + "\n")
        backup.unlink()
    except Exception:
        shutil.move(str(backup), str(config_path))
        return "error"
    return "added"


def inject_mcp_yaml(config_path: Path, data_dir: Path, namespace: str = "shared") -> SetupResult:
    """Inject lorekeeper MCP entry into a Hermes YAML config (regex-based, no PyYAML)."""
    if not config_path.exists():
        return "missing"
    content = config_path.read_text()
    mcp_match = re.search(r"^(mcp_servers:\s*\n)((?:[ \t]+[^\n]*\n)*)", content, re.MULTILINE)
    if mcp_match and re.search(r"^[ \t]+lorekeeper\s*:", mcp_match.group(0), re.MULTILINE):
        return "skip"
    ns_json = json.dumps(namespace)
    new_entry = (
        "  lorekeeper:\n"
        "    command: lorekeeper\n"
        "    args: []\n"
        "    env:\n"
        f"      LORE_DATA_DIR: {data_dir}\n"
        f"      LORE_NAMESPACE: {ns_json}\n"
    )
    if mcp_match:
        pos = mcp_match.end()
        content = content[:pos] + new_entry + content[pos:]
    else:
        content = content.rstrip() + "\nmcp_servers:\n" + new_entry
    config_path.write_text(content)
    return "added"
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_cli_setup.py -x -q -k "inject_mcp"
# Expected: all pass
```

**Step 4: Commit**

```bash
git add src/lorekeeper/cli/setup_helpers.py tests/test_cli_setup.py
git commit -m "[LKPR-77] feat: MCP config injection helpers (JSON + YAML)"
```

---

## Task 4: `setup_helpers.py` — prompt injection + skills install

**Objective:** Add `inject_prompt()` and `install_skills()` helpers, completing `setup_helpers.py`.

**Files:**

- Modify: `tests/test_cli_setup.py` — add failing tests
- Modify: `src/lorekeeper/cli/setup_helpers.py` — add the two functions

**Step 1: Add failing tests** (append to `tests/test_cli_setup.py`)

```python
from lorekeeper.cli.setup_helpers import inject_prompt, install_skills

SAMPLE_PROMPT = "## Lorekeeper\n\nUse lore_search at the start of every task.\n"


def test_inject_prompt_adds_section(tmp_path: Path) -> None:
    target = tmp_path / "soul.md"
    target.write_text("# My Agent\n\nHello.\n")
    result = inject_prompt(target, prompt_text=SAMPLE_PROMPT)
    assert result in ("added", "updated")
    assert "## Lorekeeper" in target.read_text()


def test_inject_prompt_replaces_existing(tmp_path: Path) -> None:
    target = tmp_path / "soul.md"
    target.write_text("# My Agent\n\n## Lorekeeper\n\nOld text.\n")
    result = inject_prompt(target, prompt_text="## Lorekeeper\n\nNew text.\n")
    assert result in ("added", "updated")
    content = target.read_text()
    assert "New text." in content
    assert "Old text." not in content


def test_inject_prompt_missing_file(tmp_path: Path) -> None:
    assert inject_prompt(tmp_path / "nope.md", prompt_text=SAMPLE_PROMPT) == "missing"


def test_inject_prompt_skip_identical(tmp_path: Path) -> None:
    target = tmp_path / "soul.md"
    target.write_text("# My Agent\n\n" + SAMPLE_PROMPT)
    result = inject_prompt(target, prompt_text=SAMPLE_PROMPT)
    assert result == "skip"


def test_install_skills_copies(tmp_path: Path) -> None:
    src = tmp_path / "src_skills"
    src.mkdir()
    skill = src / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nversion: 1.0.0\n---\n# My Skill\n")
    dst = tmp_path / "dst_skills"
    result = install_skills(dst, skills_src=src)
    assert "installed" in result
    assert (dst / "my-skill" / "SKILL.md").exists()


def test_install_skills_synced_when_up_to_date(tmp_path: Path) -> None:
    src = tmp_path / "src_skills"
    src.mkdir()
    skill = src / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nversion: 1.0.0\n---\n# My Skill\n")
    dst = tmp_path / "dst_skills"
    install_skills(dst, skills_src=src)
    result = install_skills(dst, skills_src=src)
    assert result == "synced"


def test_install_skills_no_src(tmp_path: Path) -> None:
    assert install_skills(tmp_path / "dst", skills_src=tmp_path / "nope") == "none"
```

**Step 2: Append to `src/lorekeeper/cli/setup_helpers.py`**

```python
def inject_prompt(target_path: Path, prompt_text: str) -> SetupResult:
    """Inject/replace the ## Lorekeeper section in a target prompt file."""
    if not target_path.exists():
        return "missing"
    content = target_path.read_text()
    if prompt_text.strip() in content:
        return "skip"
    if re.search(r"(?:^|\n)## Lorekeeper\b", content):
        content = re.sub(
            r"(?:^|\n)## Lorekeeper\b.*?(?=\n## |\Z)", "", content, flags=re.DOTALL
        )
        content = content.lstrip("\n")
        result_token: SetupResult = "updated"
    else:
        result_token = "added"
    content = content.rstrip() + "\n\n" + prompt_text.strip() + "\n"
    target_path.write_text(content)
    return result_token


def _skill_version(skill_md: Path) -> str:
    if not skill_md.exists():
        return ""
    in_front = False
    for line in skill_md.read_text().splitlines():
        if line.strip() == "---":
            if not in_front:
                in_front = True
                continue
            break
        if in_front and line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    return ""


def install_skills(target_dir: Path, skills_src: Path | None = None) -> str:
    """Install user-facing skills from assets/skills/ to target_dir.

    Returns: 'synced' | 'installed N' | 'updated N, installed M' | 'none'
    """
    if skills_src is None:
        skills_src = ASSETS_DIR / "skills"
    if not skills_src.is_dir():
        return "none"
    target_dir.mkdir(parents=True, exist_ok=True)
    n_installed = n_updated = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        src_ver = _skill_version(skill_dir / "SKILL.md")
        target = target_dir / skill_dir.name
        installed_ver = _skill_version(target / "SKILL.md")
        if src_ver and installed_ver == src_ver:
            continue
        if target.exists():
            shutil.rmtree(target)
            n_updated += 1
        else:
            n_installed += 1
        shutil.copytree(skill_dir, target)
    if n_updated == 0 and n_installed == 0:
        return "synced"
    parts = []
    if n_installed:
        parts.append(f"installed {n_installed}")
    if n_updated:
        parts.append(f"updated {n_updated}")
    return ", ".join(parts)
```

**Step 3: Run full test_cli_setup.py**

```bash
uv run pytest tests/test_cli_setup.py -x -q
# Expected: all pass
```

**Step 4: Commit**

```bash
git add src/lorekeeper/cli/setup_helpers.py tests/test_cli_setup.py
git commit -m "[LKPR-77] feat: prompt injection + skills install helpers"
```

---

## Task 5: `setup.py` — CLI orchestrator

**Objective:** Build the `lorekeeper/cli/setup.py` module that wires agent detection + helpers into an interactive `lorekeeper setup` command (with `--check` dry-run mode).

**Files:**

- Create: `src/lorekeeper/cli/setup.py`
- No new tests needed — helpers are tested; integration tested manually in Task 7

**Step 1: Create `src/lorekeeper/cli/setup.py`**

```python
"""lorekeeper setup — one-command post-pip install configuration.

Scans for Hermes, Claude Code, and Cursor. For each:
  1. Injects the lorekeeper MCP server entry
  2. Injects the lorekeeper agent prompt block
  3. Installs user-facing skills from the bundled assets/skills/

Usage:
    lorekeeper setup           # interactive
    lorekeeper setup --check   # dry-run — show what would be done, no writes
"""
from __future__ import annotations

import sys
from pathlib import Path

from lorekeeper.cli.setup_helpers import (
    ASSETS_DIR,
    AgentType,
    DetectedAgent,
    detect_agents,
    inject_mcp_json,
    inject_mcp_yaml,
    inject_prompt,
    install_skills,
)

# Default data dir (matches setup.sh behaviour)
_DEFAULT_DATA_DIR = Path.home() / ".lorekeeper"

# Prompt file bundled with the package
_PROMPT_FILE = ASSETS_DIR / "prompts" / "lorekeeper-agent-prompt.md"

# Prompt body (strip YAML frontmatter)
def _load_prompt_text() -> str:
    if not _PROMPT_FILE.exists():
        return ""
    raw = _PROMPT_FILE.read_text()
    parts = raw.split("---", 2)
    return (parts[2].strip() + "\n") if len(parts) >= 3 else raw.strip() + "\n"


def _mcp_config_path(agent: DetectedAgent) -> Path:
    if agent.type in (AgentType.HERMES_MAIN, AgentType.HERMES_PROFILE):
        return agent.dir / "config.yaml"
    if agent.type == AgentType.CLAUDE:
        return agent.dir / "settings.json"
    if agent.type == AgentType.CURSOR:
        return agent.dir / "mcp.json"
    raise ValueError(f"Unknown agent type: {agent.type}")


def _prompt_path(agent: DetectedAgent) -> Path:
    if agent.type in (AgentType.HERMES_MAIN, AgentType.HERMES_PROFILE):
        return agent.dir / "soul.md"
    if agent.type == AgentType.CLAUDE:
        return agent.dir / "CLAUDE.md"
    if agent.type == AgentType.CURSOR:
        return agent.dir / "AGENTS.md"
    raise ValueError(f"Unknown agent type: {agent.type}")


def _do_mcp(agent: DetectedAgent, data_dir: Path, dry_run: bool) -> str:
    path = _mcp_config_path(agent)
    if dry_run:
        return f"would configure {path}" if path.exists() else "missing"
    if agent.type in (AgentType.HERMES_MAIN, AgentType.HERMES_PROFILE):
        return inject_mcp_yaml(path, data_dir=data_dir, namespace=agent.namespace)
    return inject_mcp_json(path, data_dir=data_dir)


def _do_prompt(agent: DetectedAgent, prompt_text: str, dry_run: bool) -> str:
    path = _prompt_path(agent)
    if dry_run:
        return f"would inject into {path}" if path.exists() else "missing"
    return inject_prompt(path, prompt_text=prompt_text)


def _do_skills(agent: DetectedAgent, dry_run: bool) -> str:
    target = agent.dir / "skills"
    if dry_run:
        return f"would install to {target}"
    return install_skills(target)


def _cell(val: str) -> str:
    if val in ("added", "updated") or val.startswith("installed") or val.startswith("updated"):
        return f"✓ {val}"
    if val == "skip" or val == "synced" or val.startswith("already"):
        return f"→ {val}"
    if val == "missing":
        return "! missing"
    if val == "error":
        return "✗ error"
    return val


def run_setup(dry_run: bool = False, data_dir: Path | None = None) -> int:
    """Main entrypoint for `lorekeeper setup [--check]`.

    Returns exit code: 0 = ok, 1 = error.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    print("Lorekeeper setup")
    print(f"  data:    {data_dir}")
    print(f"  assets:  {ASSETS_DIR}")
    if dry_run:
        print("  mode:    --check (dry run — no writes)")
    print()

    agents = detect_agents()
    if not agents:
        print("! No agents detected.")
        print("  Install Hermes (~/.hermes/), Claude Code (~/.claude/),")
        print("  or Cursor (~/.cursor/) first.")
        return 0

    print(f"Found {len(agents)} agent(s):")
    for a in agents:
        print(f"  ☑ {a.name}  — {a.dir}")
    print()

    if not dry_run:
        answer = input("Configure these? [Y/n] ").strip()
        if answer.lower() in ("n", "no"):
            print("Skipping.")
            return 0

    prompt_text = _load_prompt_text()

    results: list[tuple[str, str, str, str]] = []
    for agent in agents:
        mcp_r = _do_mcp(agent, data_dir=data_dir, dry_run=dry_run)
        prompt_r = _do_prompt(agent, prompt_text=prompt_text, dry_run=dry_run)
        skills_r = _do_skills(agent, dry_run=dry_run)
        results.append((agent.name, mcp_r, prompt_r, skills_r))

    print()
    print("Setup summary")
    header = f"{'Agent':<30}  {'MCP':<18}  {'Prompt':<18}  Skills"
    print(header)
    print("─" * len(header))
    for name, mcp, prompt, skills in results:
        print(f"{name:<30}  {_cell(mcp):<18}  {_cell(prompt):<18}  {_cell(skills)}")

    print()
    if not dry_run:
        print("Restart each agent to activate Lorekeeper.")
        print()
        _print_seed_prompt()

    return 0


def _print_seed_prompt() -> None:
    print("─────────────────────────────────────────")
    print("  Seed your first memories!")
    print("─────────────────────────────────────────")
    print()
    print("  Paste this into any connected agent:")
    print()
    print("    Read your prompt/config files (soul.md,")
    print("    CLAUDE.md, .cursorrules, AGENTS.md) and")
    print("    save key facts about yourself to Lorekeeper")
    print("    using lore_remember or lore_insert.")
    print()
    print("  Then open the dashboard to see what it learned!")
    print("    lorekeeper-dashboard")
    print("    → http://127.0.0.1:7777")
    print("─────────────────────────────────────────")
    print()
```

**Step 2: Lint check**

```bash
uv run ruff check src/lorekeeper/cli/setup.py
# Expected: no errors
```

**Step 3: Commit**

```bash
git add src/lorekeeper/cli/setup.py
git commit -m "[LKPR-77] feat: setup CLI orchestrator (run_setup + dry-run)"
```

---

## Task 6: Wire `lorekeeper setup` into `__main__.py`

**Objective:** Add `setup` subcommand to the existing argparse entrypoint so `lorekeeper setup` and `lorekeeper setup --check` work, while `lorekeeper` (no args) still starts the MCP server.

**Files:**

- Modify: `src/lorekeeper/__main__.py`

**Step 1: Read current `__main__.py`** (already read above, 24 lines — argparse, no subcommands)

**Step 2: Replace `__main__.py`**

```python
import argparse
import sys

from lorekeeper.config import Settings
from lorekeeper.logging_setup import configure_logging
from lorekeeper.server import init_service, mcp


def _run_mcp_server() -> None:
    settings = Settings()
    configure_logging(log_dir=settings.log_dir)
    init_service(settings)
    mcp.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lorekeeper",
        description="Self-improving MCP memory server for AI agents.",
    )
    sub = parser.add_subparsers(dest="command")

    # setup subcommand
    setup_p = sub.add_parser("setup", help="Configure AI agents to use Lorekeeper.")
    setup_p.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: show what would be configured without writing anything.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        from lorekeeper.cli.setup import run_setup
        sys.exit(run_setup(dry_run=args.check))
    else:
        # Default (no subcommand): run MCP server — preserves backward compat
        _run_mcp_server()


if __name__ == "__main__":
    main()
```

**Step 3: Verify help text**

```bash
uv run lorekeeper --help
# Expected: shows "setup" as a subcommand

uv run lorekeeper setup --help
# Expected: shows --check flag
```

**Step 4: Smoke-test dry run**

```bash
uv run lorekeeper setup --check
# Expected: shows detected agents, prints "would configure" lines, no writes
```

**Step 5: Commit**

```bash
git add src/lorekeeper/__main__.py
git commit -m "[LKPR-77] feat: wire setup subcommand into __main__.py"
```

---

## Task 7: mypy + full test suite clean

**Objective:** Pass mypy strict + all unit tests before opening the PR.

**Files:**

- Modify: `src/lorekeeper/cli/setup_helpers.py` — fix any type errors
- Modify: `src/lorekeeper/cli/setup.py` — fix any type errors

**Step 1: Run mypy**

```bash
uv run mypy src/lorekeeper/cli/
# Fix any errors. Common: missing return types, str vs Path, Literal mismatches.
```

**Step 2: Run full unit suite**

```bash
uv run pytest -x -q
# Expected: all green
```

**Step 3: Run ruff on all touched files**

```bash
uv run ruff check src/lorekeeper/cli/ src/lorekeeper/__main__.py tests/test_cli_setup.py
# Expected: no errors
```

**Step 4: Commit any fixes**

```bash
git add -p
git commit -m "[LKPR-77] fix: mypy + lint cleanup"
```

---

## Task 8: Update docs and move ticket to done

**Objective:** Update CLAUDE.md tooling section, README Quick Start, docs/quickstart.md with `lorekeeper setup` as step 2. Move ticket to `done/`.

**Files:**

- Modify: `CLAUDE.md` — add `lorekeeper setup` to tooling section
- Modify: `README.md` — update Quick Start (add step 2: `lorekeeper setup`)
- Modify: `docs/quickstart.md` — replace manual config steps with `lorekeeper setup`
- Move: `backlogs/LKPR-77-cli-setup-command.md` → `backlogs/done/LKPR-77-cli-setup-command.md`

**Step 1: Update CLAUDE.md tooling section**

Find the tooling/scripts section in CLAUDE.md and add:

```
- `lorekeeper setup` — one-command post-pip install (agent detection, MCP injection, prompt + skills install)
- `lorekeeper setup --check` — dry-run mode
```

**Step 2: Update README.md Quick Start**

The current Quick Start is 3 steps (install, start, connect). Revise to:

````markdown
## Quick Start

3 minutes, zero configuration:

```bash
# 1. Install
pip install lorekeeper-mcp

# 2. Configure your agents (one command)
lorekeeper setup

# 3. Start the MCP server
lorekeeper
```
````

`lorekeeper setup` scans for Hermes, Claude Code, and Cursor — injects the MCP entry, installs the agent prompt, and copies the bundled skills. Restart your agent after setup.

````

**Step 3: Update docs/quickstart.md**

Replace the manual "Connect your agent" section (current step 2) with:

```markdown
## 2. Configure your agents

Run the setup command — it auto-detects Hermes, Claude Code, and Cursor:

```bash
lorekeeper setup
````

It will show which agents it found and ask for confirmation before writing. To preview without changes:

```bash
lorekeeper setup --check
```

**Manual config (if you prefer):** See the [Manual Configuration](#manual-configuration) section below.

````

**Step 4: Move ticket**

```bash
cd /Users/jessinra/Code/lorekeeper
git mv backlogs/LKPR-77-cli-setup-command.md backlogs/done/LKPR-77-cli-setup-command.md
````

**Step 5: Commit**

```bash
git add CLAUDE.md README.md docs/quickstart.md backlogs/
git commit -m "[LKPR-77] chore: update docs + move ticket to done"
```

---

## Task 9: Open PR

**Objective:** Push branch, open PR, self-review, merge.

**Step 1: Final lint + type check sweep**

```bash
cd /Users/jessinra/Code/lorekeeper
uv run ruff check src tests
uv run mypy src
uv run pytest -x -q
# All green
```

**Step 2: Push**

```bash
git push -u origin lkpr-77-cli-setup-command
```

**Step 3: Open PR via GitHub API**

Use urllib.request (gh CLI won't work for App token — per project convention):

```python
import urllib.request, json, os

token = os.environ["GH_TOKEN"]  # refreshed via gh-token-refresh.py
body = {
    "title": "[LKPR-77] feat: lorekeeper setup CLI command — one-command install",
    "head": "lkpr-77-cli-setup-command",
    "base": "main",
    "body": "## Summary\n\nPorts `scripts/setup.sh` agent detection + config injection into a `lorekeeper setup` Python CLI subcommand bundled with the pip package.\n\n## Changes\n- New `src/lorekeeper/cli/` package: `setup_helpers.py` + `setup.py`\n- Assets moved to `src/lorekeeper/assets/` for wheel bundling\n- `__main__.py` wired with argparse subcommand\n- `lorekeeper setup --check` dry-run mode\n- Docs updated: README, quickstart, CLAUDE.md\n\n## Testing\n- Unit tests: `tests/test_cli_setup.py` covers all helpers\n- Manual smoke: `lorekeeper setup --check` shows correct output\n\nFixes #172",
}
req = urllib.request.Request(
    "https://api.github.com/repos/Jessinra/Lorekeeper/pulls",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as r:
    pr = json.loads(r.read())
    print(pr["html_url"])
```

**Step 4: Self-review and merge**

Review the diff (`git log origin/main..HEAD --stat`), then merge via API or GitHub UI.

---

## Acceptance Criteria Checklist

- [ ] `lorekeeper setup` runs from a `pip install lorekeeper-mcp` install (no git clone)
- [ ] Detects Hermes main, Hermes profiles, Claude Code, Cursor
- [ ] Injects MCP entry into each detected agent's config
- [ ] Injects lorekeeper agent prompt into soul.md / CLAUDE.md / AGENTS.md
- [ ] Installs bundled `assets/skills/` into each agent's skills dir
- [ ] `lorekeeper setup --check` shows what would happen, no writes
- [ ] `lorekeeper` (no args) still starts the MCP server (backward compat)
- [ ] Unit tests: all helpers covered
- [ ] mypy strict: no errors
- [ ] ruff: no errors
- [ ] Docs updated (README, quickstart, CLAUDE.md)
- [ ] Ticket moved to `backlogs/done/`
