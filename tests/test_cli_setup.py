"""Tests for lorekeeper CLI setup helpers — agent detection and config injection."""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch as mock_patch

from lorekeeper.cli.setup import run_setup
from lorekeeper.cli.setup_helpers import (
    AgentType,
    DetectedAgent,
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


# ── run_setup() integration ────────────────────────────────────────────────────


def _make_hermes_home(tmp_path: Path) -> Path:
    """Create minimal .hermes home so detect_agents() finds exactly one agent."""
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    (hermes / "config.yaml").write_text("model: test\n")
    (hermes / "soul.md").write_text("# Agent\n")
    return tmp_path


def test_run_setup_check_mode_no_writes(tmp_path: Path) -> None:
    """--check mode: no writes, returns 0, no interactive prompt."""
    home = _make_hermes_home(tmp_path)
    agents = detect_agents(home=home)
    _prompt = "## Lorekeeper\n\nTest.\n"
    with mock_patch("lorekeeper.cli.setup._load_prompt_text", return_value=_prompt), \
         mock_patch("lorekeeper.cli.setup.detect_agents", return_value=agents):
        code = run_setup(dry_run=True, data_dir=tmp_path / ".lorekeeper")
    assert code == 0
    # No config.yaml write should have happened in the hermes dir
    content = (tmp_path / ".hermes" / "config.yaml").read_text()
    assert "lorekeeper" not in content


def test_run_setup_interactive_skip(tmp_path: Path, capsys) -> None:
    """User types 'n': setup skips, returns 0, no config written."""
    home = _make_hermes_home(tmp_path)
    agents = detect_agents(home=home)
    with mock_patch("lorekeeper.cli.setup.detect_agents", return_value=agents), \
         mock_patch("builtins.input", return_value="n"):
        code = run_setup(dry_run=False, data_dir=tmp_path / ".lorekeeper")
    assert code == 0
    captured = capsys.readouterr()
    assert "Skipping" in captured.out


def test_run_setup_error_returns_nonzero(tmp_path: Path) -> None:
    """If any step returns 'error', run_setup returns exit code 1."""
    bad_agent = DetectedAgent(
        name="TestAgent", type=AgentType.CLAUDE, dir=tmp_path / ".claude", namespace="shared"
    )
    with mock_patch("lorekeeper.cli.setup.detect_agents", return_value=[bad_agent]), \
         mock_patch("lorekeeper.cli.setup._do_mcp", return_value="error"), \
         mock_patch("lorekeeper.cli.setup._do_prompt", return_value="skip"), \
         mock_patch("lorekeeper.cli.setup._do_skills", return_value="synced"), \
         mock_patch("builtins.input", return_value="y"):
        code = run_setup(dry_run=False, data_dir=tmp_path / ".lorekeeper")
    assert code == 1


def test_run_setup_respects_lore_data_dir_env(tmp_path: Path, monkeypatch) -> None:
    """LORE_DATA_DIR env var should override the default ~/.lorekeeper path."""
    custom_dir = tmp_path / "custom_data"
    monkeypatch.setenv("LORE_DATA_DIR", str(custom_dir))
    home = _make_hermes_home(tmp_path)
    agents = detect_agents(home=home)
    output = io.StringIO()
    with mock_patch("lorekeeper.cli.setup.detect_agents", return_value=agents), \
         mock_patch("sys.stdout", output), \
         mock_patch("builtins.input", return_value="n"):
        run_setup(dry_run=False)
    assert str(custom_dir) in output.getvalue()
