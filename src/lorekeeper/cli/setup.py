"""lorekeeper setup — one-command post-pip install configuration.

Scans for Hermes, Claude Code, and Cursor. For each agent:
  1. Injects the lorekeeper MCP server entry into the agent's config
  2. Injects the lorekeeper agent prompt block into soul.md / CLAUDE.md / AGENTS.md
  3. Installs user-facing skills from the bundled assets/skills/

Usage:
    lorekeeper setup           # interactive
    lorekeeper setup --check   # dry-run — show what would be done, no writes
"""
from __future__ import annotations

import os
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


def _load_prompt_text() -> str:
    """Load prompt text, stripping YAML frontmatter if present."""
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
    raise ValueError(f"Unknown agent type: {agent.type}")  # pragma: no cover


def _prompt_path(agent: DetectedAgent) -> Path:
    if agent.type in (AgentType.HERMES_MAIN, AgentType.HERMES_PROFILE):
        return agent.dir / "soul.md"
    if agent.type == AgentType.CLAUDE:
        return agent.dir / "CLAUDE.md"
    if agent.type == AgentType.CURSOR:
        return agent.dir / "AGENTS.md"
    raise ValueError(f"Unknown agent type: {agent.type}")  # pragma: no cover


def _do_mcp(agent: DetectedAgent, data_dir: Path, dry_run: bool) -> str:
    path = _mcp_config_path(agent)
    if dry_run:
        if path.exists():
            return f"would configure {path}"
        return f"would create and configure {path}"
    # Ensure config file exists (like setup.sh — creates empty JSON for fresh agents)
    if not path.exists():
        if agent.type in (AgentType.HERMES_MAIN, AgentType.HERMES_PROFILE):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("mcp_servers:\n")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n")
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
    if val in ("skip", "synced") or val.startswith("already"):
        return f"→ {val}"
    if val == "missing":
        return "! missing"
    if val == "error":
        return "✗ error"
    return val


def run_setup(dry_run: bool = False, data_dir: Path | None = None) -> int:
    """Main entrypoint for ``lorekeeper setup [--check]``.

    Returns exit code: 0 = ok, 1 = error.
    """
    if data_dir is None:
        env_val = os.environ.get("LORE_DATA_DIR")
        data_dir = Path(env_val) if env_val else _DEFAULT_DATA_DIR

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
        print(f"  \u2611 {a.name}  \u2014 {a.dir}")
    print()

    if not dry_run:
        try:
            answer = input("Configure these? [Y/n] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSkipping.")
            return 0
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
    header = f"{'Agent':<30}  {'MCP':<24}  {'Prompt':<24}  Skills"
    print(header)
    print("\u2500" * len(header))
    has_errors = False
    for name, mcp, prompt, skills in results:
        print(f"{name:<30}  {_cell(mcp):<24}  {_cell(prompt):<24}  {_cell(skills)}")
        if "error" in (mcp, prompt, skills):
            has_errors = True

    print()
    if has_errors:
        print("! One or more steps reported an error — check agent configs above.")
    elif not dry_run:
        print("Restart each agent to activate Lorekeeper.")
        print()
        _print_seed_prompt()

    return 1 if has_errors else 0


def _print_seed_prompt() -> None:
    print("\u2500" * 43)
    print("  Seed your first memories!")
    print("\u2500" * 43)
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
    print("    \u2192 http://127.0.0.1:7777")
    print("\u2500" * 43)
    print()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_setup())
