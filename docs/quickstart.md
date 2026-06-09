# Quickstart: Get Lorekeeper running in 2 minutes

> From zero to your agent's first persistent memory.

---

## 1. Install

```bash
pip install lorekeeper-mcp
```

**Verify it works:**

```bash
lorekeeper --help
# usage: lorekeeper [-h] {setup} ...
#
# Self-improving MCP memory server for AI agents.
#
# positional arguments:
#   {setup}
#     setup     Configure AI agents to use Lorekeeper.
#
# options:
#   -h, --help  show this help message and exit
#
# Run without arguments to start the MCP server.
```

> **Pro tip:** `lorekeeper` (no flags) starts the MCP server. It runs until you stop it with `Ctrl+C`. If you see the help text, the install worked.

---

## 2. Configure your agents

Run the one-command setup — it auto-detects Hermes, Claude Code, and Cursor:

```bash
lorekeeper setup
```

It will show which agents it found and ask for confirmation before writing. To preview without changes:

```bash
lorekeeper setup --check
```

Restart each agent after setup. You'll see 8 new MCP tools available.

**Manual config (if you prefer):** expand the sections below.

<details>
<summary>Manual: Claude Code</summary>

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "lorekeeper",
      "args": [],
      "env": {}
    }
  }
}
```

</details>

<details>
<summary>Manual: Cursor</summary>

Settings → MCP Servers → Add:

| Field   | Value        |
| ------- | ------------ |
| Name    | `lorekeeper` |
| Type    | `command`    |
| Command | `lorekeeper` |
| Args    | _(empty)_    |

</details>

<details>
<summary>Manual: Hermes Agent</summary>

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  lorekeeper:
    command: lorekeeper
    args: []
    env: {}
```

</details>

---

## 3. Save your first memory

Ask your agent to remember something:

> _"Remember that my favorite debug command is `curl -vX GET` for checking REST endpoints."_

The agent calls `lore_remember({"thought": "..."})`. ✅ Memory stored.

You can also ask it directly:

> _"Search for my favorite debug command."_

The agent calls `lore_search({"query": "debug command"})`. ✅ Memory retrieved.

---

## 4. Make it automatic

Add this to your agent's prompt file (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`, or `soul.md`):

```markdown
## Lorekeeper

At the start of every task, search Lorekeeper for relevant context.
After the task, save new discoveries with `lore_remember` or `lore_insert`.
```

Now every session starts with context and saves what it learns.

---

## 5. See everything in the dashboard

```bash
lorekeeper-dashboard
# → http://127.0.0.1:7777
```

Browse, search, edit, and manage all your memories. Seven tabs:

| Tab          | What it shows                                          |
| ------------ | ------------------------------------------------------ |
| **Memories** | All stored memories with scores, usage, dates          |
| **Detail**   | Edit, delete, manage links per memory                  |
| **Links**    | Knowledge graph connections between memories           |
| **Query**    | Ad-hoc semantic + keyword search                       |
| **Sessions** | Processed agent sessions with extracted learnings      |
| **Config**   | Live tuning of search weights, quality signals, limits |
| **Backup**   | Export/import memories as JSON                         |

---

## What's next

| Goal                        | Resource                                                       |
| --------------------------- | -------------------------------------------------------------- |
| Full MCP tool reference     | `README.md` → **MCP tools** section                            |
| Understand the architecture | `docs/ARCHITECTURE.md`                                         |
| Development setup           | `README.md` → **Development** section                          |
| Report a bug                | [GitHub Issues](https://github.com/Jessinra/Lorekeeper/issues) |
| Strategy & positioning      | `docs/positioning-manifesto.md`                                |

---

_Your first memory is stored at `~/.lorekeeper/`. Everything is local. Nothing leaves your machine._
