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
        agents.append(
            DetectedAgent(
                name="Hermes (main)",
                type=AgentType.HERMES_MAIN,
                dir=hermes_dir,
                namespace="shared",
            )
        )
        profiles_dir = hermes_dir / "profiles"
        if profiles_dir.is_dir():
            for profile_dir in sorted(profiles_dir.iterdir()):
                if profile_dir.is_dir():
                    agents.append(
                        DetectedAgent(
                            name=f"Hermes (profile: {profile_dir.name})",
                            type=AgentType.HERMES_PROFILE,
                            dir=profile_dir,
                            namespace=profile_dir.name,
                        )
                    )

    claude_dir = home / ".claude"
    if claude_dir.is_dir() or (claude_dir / "settings.json").exists():
        agents.append(
            DetectedAgent(
                name="Claude Code",
                type=AgentType.CLAUDE,
                dir=claude_dir,
                namespace="shared",
            )
        )

    cursor_dir = home / ".cursor"
    if cursor_dir.is_dir() or (cursor_dir / "mcp.json").exists():
        agents.append(
            DetectedAgent(
                name="Cursor",
                type=AgentType.CURSOR,
                dir=cursor_dir,
                namespace="shared",
            )
        )

    return agents


# ── MCP injection ──────────────────────────────────────────────────────────────


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


def inject_mcp_yaml(
    config_path: Path, data_dir: Path, namespace: str = "shared"
) -> SetupResult:
    """Inject lorekeeper MCP entry into a Hermes YAML config (regex-based, no PyYAML)."""
    if not config_path.exists():
        return "missing"
    content = config_path.read_text()
    mcp_match = re.search(
        r"^(mcp_servers:\s*\n)((?:[ \t]+[^\n]*\n)*)", content, re.MULTILINE
    )
    if mcp_match and re.search(
        r"^[ \t]+lorekeeper\s*:", mcp_match.group(0), re.MULTILINE
    ):
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


# ── Prompt injection ───────────────────────────────────────────────────────────


def inject_prompt(target_path: Path, prompt_text: str) -> SetupResult:
    """Inject/replace the ## Lorekeeper section in a target prompt file."""
    if not target_path.exists():
        return "missing"
    content = target_path.read_text()
    if prompt_text.strip() in content:
        return "skip"
    result_token: SetupResult
    if re.search(r"(?:^|\n)## Lorekeeper\b", content):
        content = re.sub(
            r"(?:^|\n)## Lorekeeper\b.*?(?=\n## |\Z)", "", content, flags=re.DOTALL
        )
        content = content.lstrip("\n")
        result_token = "updated"
    else:
        result_token = "added"
    content = content.rstrip() + "\n\n" + prompt_text.strip() + "\n"
    target_path.write_text(content)
    return result_token


# ── Skills installation ────────────────────────────────────────────────────────


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

    Returns: 'synced' | 'installed N' | 'updated N' | 'installed N, updated M' | 'none'
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
