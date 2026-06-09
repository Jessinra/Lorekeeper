"""Tests for lorekeeper CLI setup helpers — agent detection and config injection."""
from __future__ import annotations

import json
from pathlib import Path

from lorekeeper.cli.setup_helpers import (
    AgentType,
    detect_agents,
    inject_mcp_json,
    inject_mcp_yaml,
    inject_prompt,
    install_skills,
)

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
    assert inject_mcp_yaml(
        tmp_path / "nope.yaml", data_dir=tmp_path, namespace="shared"
    ) == "missing"


def test_inject_mcp_yaml_profile_namespace(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("model: claude\n")
    inject_mcp_yaml(cfg, data_dir=tmp_path / ".lorekeeper", namespace="diana")
    content = cfg.read_text()
    assert "'diana'" in content
    # Data dir path should also be YAML-quoted
    assert "'" + str(tmp_path / ".lorekeeper") + "'" in content


# ── Prompt injection ───────────────────────────────────────────────────────────

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


def test_inject_prompt_empty_text_returns_error(tmp_path: Path) -> None:
    target = tmp_path / "soul.md"
    target.write_text("# My Agent\n")
    result = inject_prompt(target, prompt_text="")
    assert result == "error"


# ── Skills installation ────────────────────────────────────────────────────────


_SKILL_MD = (
    "---\nname: my-skill\nversion: 1.0.0\ndescription: test\n---\n# My Skill\n"
)


def test_install_skills_copies(tmp_path: Path) -> None:
    src = tmp_path / "src_skills"
    src.mkdir()
    skill = src / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(_SKILL_MD)
    dst = tmp_path / "dst_skills"
    result = install_skills(dst, skills_src=src)
    assert "installed" in result
    assert (dst / "my-skill" / "SKILL.md").exists()


def test_install_skills_synced_when_up_to_date(tmp_path: Path) -> None:
    src = tmp_path / "src_skills"
    src.mkdir()
    skill = src / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(_SKILL_MD)
    dst = tmp_path / "dst_skills"
    install_skills(dst, skills_src=src)
    result = install_skills(dst, skills_src=src)
    assert result == "synced"


def test_install_skills_no_src(tmp_path: Path) -> None:
    assert install_skills(tmp_path / "dst", skills_src=tmp_path / "nope") == "none"
