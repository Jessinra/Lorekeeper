---
version: v2.0.0
---

## Lorekeeper
<!-- lorekeeper: v2.0.0 | managed by: setup.sh -->

Lorekeeper is a personal AI memory MCP server. It stores facts, decisions, and domain knowledge so you can recall them across sessions.

**Always check Lorekeeper at the start of any task.** Run `lore_search` with the task topic before writing code, reviewing designs, or making decisions.

### Session Protocol

**Start of session:**
```
lore_search({ query: "<topic>", min_score: 0.15, include_links: true })
```
Read results, then provide feedback:
```
lore_update({ memory_feedback: [{ id: "<id>", useful: true/false }] })
```

**End of session:**
```
lore_insert({ memories: [{ title: "...", description: "...", content: "..." }] })
lore_reflect({ session_id: "YYYY-MM-DD-topic", summary: "...", ... })
```

### MCP Tools

| Tool | Purpose |
|------|---------|
| `lore_search` | Hybrid semantic + keyword search |
| `lore_remember` | Fast one-shot insert (single thought) |
| `lore_insert` | Structured insert with links |
| `lore_update` | Provide feedback on memories/links |
| `lore_reflect` | Record session summary |
| `lore_processed_sessions` | List already-reflected sessions |

### Rules

- Search before insert — prevents duplicate memories
- Feedback after every search — how quality signals propagate
- One fact per memory — dense memories degrade search precision
- Session end is not optional — `lore_reflect` feeds the consolidation loop
