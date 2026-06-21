# Lorekeeper Skills for Agents

These skills are loaded by agents that use the Lorekeeper MCP server. Each skill teaches a specific workflow — searching, memorizing, linking, reconciling, or following the session protocol.

## Available Skills

- **`lorekeeper-link-memories`** — Discover and create typed relationships between memories using `lore_recommend_links`. Surfaces high-confidence link candidates scored by cosine similarity, BM25, entity overlap, and temporal proximity.
- **`lorekeeper-memorize`** — Proactively capture important facts, user instructions, discoveries, and knowledge into Lorekeeper. Always searches for related memories and creates links.
- **`lorekeeper-protocol`** — Full session protocol for using Lorekeeper MCP tools: when and how to search, insert, update, reflect across all three session phases.
- **`lorekeeper-reconcile`** — Reconcile and fact-check memories against source materials, documentation, and internal consistency. Updates scores and soft-deletes incorrect facts.
- **`lorekeeper-search`** — Search the knowledge base with hybrid semantic + keyword retrieval and provide relevance feedback with confidence ratings.
