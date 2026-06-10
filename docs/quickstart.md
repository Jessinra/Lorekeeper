# Quickstart

Get Lorekeeper running and seeding memories in **~2 min** (warm cache) or **~5 min** on first
install (sentence-transformers model download is ~90 MB).

---

## Prerequisites

- Python 3.11+ ([`uv python install 3.11`](https://github.com/astral-sh/uv) if missing)
- [`uv`](https://github.com/astral-sh/uv) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- One of: **Hermes Agent**, **Claude Code**, or **Cursor**

---

## 1 — Install & configure

```bash
pip install lorekeeper-mcp
lorekeeper setup
```

If you are working from a git checkout, `bash scripts/setup.sh` still exists and also installs

development hooks/skills. For the primary PyPI install path, `lorekeeper setup` is the command
to run.

What this does:

- Installs the package and bundled CLI
- Creates `~/.lorekeeper/` (data directory)
- Auto-detects Hermes / Claude Code / Cursor and injects MCP config + prompt section
- Installs skills for each detected agent
- Prints a **seed prompt** — keep the terminal open for step 5

---

## 2 — Restart your agent

After `setup.sh` finishes, **restart your agent** (Claude Code, Hermes, or Cursor) to load the
new MCP config. The `lorekeeper` MCP server starts automatically on the next agent launch.

---

## 3 — Start the dashboard

In a separate terminal:

```bash
uv run lorekeeper-dashboard
```

Then open: **http://127.0.0.1:7777**

The dashboard starts empty — memories appear here in real time as you insert them.

> Change the port: `LORE_DASH_PORT=8888 uv run lorekeeper-dashboard`

---

## 4 — Seed your first memories

Copy the seed prompt printed at the end of `setup.sh` and paste it into your agent:

```
Read your prompt/config files (soul.md, CLAUDE.md, .cursorrules, AGENTS.md) and
save key facts about yourself to Lorekeeper using lore_remember or lore_insert — who you
are, what you do, your constraints and preferences. Be thorough.
```

The agent will call `lore_remember` / `lore_insert` and the dashboard will populate.

---

## 5 — Verify MCP round-trip

In your agent, run these two back-to-back:

```
lore_remember("My first test memory")
lore_search("test memory")
```

Expected `lore_search` result — you should see the memory you just stored:

```json
{
  "memories": [
    {
      "title": "My first test memory",
      "combined_score": 0.87
    }
  ],
  "count": 1
}
```

---

## CLI flags

The `lorekeeper` binary now accepts `--help` and `--version` without starting the MCP server:

```bash
lorekeeper --help
# usage: lorekeeper [-h] [--version] {setup} ...
# Personal AI memory MCP server — stores facts and knowledge for AI agents.

lorekeeper --version
# lorekeeper 0.2.0
```

> `uv run lorekeeper --help` works too if the binary isn't on PATH.

---

## Troubleshooting

**`lorekeeper: command not found`**

The binary is only on PATH if installed via `uv tool install` or a virtualenv. Use
`uv run lorekeeper` from inside the repo, or run:

```bash
uv tool install ./dist/lorekeeper_mcp-0.2.0-py3-none-any.whl
```

---

**Dashboard is empty after seeding**

1. Check that the agent actually called `lore_remember` / `lore_insert` (look at the agent's
   tool call log).
2. Confirm the MCP server connected — if not, re-run `bash scripts/setup.sh` and restart the
   agent.
3. Hard-refresh the dashboard (`Cmd+Shift+R`).

---

**MCP tools not available in agent**

- Confirm `setup.sh` ran without errors and showed your agent in the summary table.
- Check the agent's MCP config file for a `lorekeeper` entry:
  - Claude Code: `~/.claude/settings.json`
  - Cursor: `~/.cursor/mcp.json`
  - Hermes: `~/.hermes/mcp.yml`
- Restart the agent if you edited config manually.

---

## Next steps

- Browse all available tools: [`lore_search`, `lore_remember`, `lore_insert`, `lore_update`,
  `lore_forget`, `lore_reflect`, `lore_recommend_links`, `lore_processed_sessions`]
- Full configuration reference: [README.md — Configuration](../README.md#configuration)
- Architecture deep-dive: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
