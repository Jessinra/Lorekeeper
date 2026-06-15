# X/Twitter Launch Thread

---

**Tweet 1:**

Every AI coding session starts blank. You re-explain context, re-state preferences, re-teach patterns — every single time.

Lorekeeper is a local MCP memory server that remembers across sessions. And it gets better the more you use it.

`pip install lorekeeper-mcp && lorekeeper setup`

---

**Tweet 2:**

The twist: a feedback loop.

Agent finds a memory → rates it useful or not → scores adjust → weak memories fade → strong ones rise.

A 6-month-old install is genuinely different from a fresh one. Less noise, sharper recall.

---

**Tweet 3:**

On LongMemEval-S benchmark (500 questions):

• R@1: 84.6%
• R@5: 96.6%
• R@10: 98.8%
• Latency: 33ms/query

Runs on the standard all-MiniLM-L6-v2 — no proprietary embeddings, no cloud API.

---

**Tweet 4:**

What else ships:

• Hybrid search (vectors + BM25 + time-decay + usage)
• Auto-linking knowledge graph
• Dashboard UI (browse, edit, query)
• Namespaces for multi-agent setups
• 8 MCP tools — works with Claude Code, Cursor, Hermes, Codex, Copilot

---

**Tweet 5:**

Local-first. SQLite + LanceDB on your disk. No API keys, no sign-up, no cloud. Apache 2.0.

Built by agents, for agents — every tool was shaped by the agents using it daily.

GitHub → https://github.com/Jessinra/Lorekeeper