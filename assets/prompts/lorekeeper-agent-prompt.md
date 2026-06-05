---
version: v2.2.0
---

## Lorekeeper

<!-- lorekeeper: v2.1.1 | managed by: setup.sh -->

Lorekeeper is a personal AI memory MCP server.
It stores facts, decisions, and domain knowledge so you can recall them across sessions.
Use it actively.

**At the start of every task:** search Lorekeeper for relevant context before doing work.

```
mcp_lorekeeper_lore_search(query="...")
```

**During work:** re-search if the context shifts.

**At the end of every task:**

1. `mcp_lorekeeper_lore_update` — give feedback on memories you retrieved (confidence 1-10)
2. `mcp_lorekeeper_lore_insert` — save new facts, code discoveries, pitfalls, or engineering decisions

This is not optional — it's how you build institutional knowledge about the Lorekeeper codebase over time.

### Skills

| Skill                     | Description                                                                   |
|---------------------------|-------------------------------------------------------------------------------|
| `lorekeeper-protocol`     | Full session protocol for using Lorekeeper MCP tools correctly                |
| `lorekeeper-memorize`     | Memorize important facts, user instructions, and discoveries                  |
| `lorekeeper-search`       | Search memory and provide relevance feedback with confidence ratings          |
| `lorekeeper-link-memories`| Discover typed relationships between memories via `lore_recommend_links`      |

### Rules

- Save code patterns, API quirks, pitfall discoveries, engineering decisions
- Don't save task progress or temporary state
- Write memories as facts, not instructions to yourself
- One fact per memory — dense memories degrade search precision
- If something is stale or wrong, update it via `lore_update`

### MCP Tools

| Tool                   | Purpose                                                                       |
|------------------------|-------------------------------------------------------------------------------|
| `lore_search`          | Hybrid semantic + keyword search                                              |
| `lore_remember`        | Fast one-shot insert (single thought)                                         |
| `lore_insert`          | Structured insert with links                                                  |
| `lore_update`          | Provide feedback on memories/links                                            |
| `lore_recommend_links` | Suggest link candidates between memories, confirm with `lore_insert`          |
