# Show HN: Lorekeeper — Self-Improving Memory for AI Agents

**One command, no cloud, no config.**

```
pip install lorekeeper-mcp && lorekeeper setup && lorekeeper
```

## What it is

Every AI coding session starts blank. You re-explain context, re-state preferences, re-teach patterns — every single time.

Files like `CLAUDE.md` and `.cursorrules` help, but they're hand-maintained and grow stale. Cloud memory services work, but your data leaves your machine and you're paying per API call.

Lorekeeper is a different approach: **a local MCP memory server you `pip install` once.** It sits alongside your agents (Claude Code, Cursor, Hermes, Codex, Copilot) and persists everything they learn — with a twist.

## The twist: it gets better with use

Most memory stores are buckets. You put memories in, you search for them later. Lorekeeper has a **feedback loop**:

> Agent finds a memory → rates it useful or not → scores adjust automatically → weak memories decay → strong ones surface more → search gets sharper

A six-month-old install is genuinely different from a fresh one. The longer you use it, the less noise you get.

## What ships

- **Hybrid search** — semantic vectors + BM25 keyword + time-decay + usage frequency + memory score, all ranked by a weighted formula
- **Auto-linking** — new memories are automatically linked to their closest semantic neighbor. A knowledge graph forms without effort
- **Duplicate detection** — near-identical content is blocked automatically
- **Dashboard** — full web UI to browse, search, edit, manage memories
- **Namespaces** — multiple agents share one store with isolated namespaces
- **Reflection** — agents auto-extract learnings from sessions. Discoveries become searchable memories
- **8 MCP tools** covering the full memory lifecycle

## Benchmarks

On the standard LongMemEval-S benchmark (500 questions, ICLR 2025):

| Metric | Value | Latency |
|--------|-------|---------|
| R@1 | **84.6%** | 32.9 ms |
| R@5 | **96.6%** | — |
| R@10 | **98.8%** | — |

Comparison: agentmemory reports 95.2% R@5 on the same benchmark. Lorekeeper's 96.6% R@5 is slightly higher, running on the standard `all-MiniLM-L6-v2` embedding model (no proprietary embeddings).

## Why open-source matters here

Lorekeeper is itself built **by AI agents**. Every tool schema, return type, and workflow was shaped by agents using it daily — not by humans reading specs. The repo is a working demo of what it does.

## Quick start

```bash
pip install lorekeeper-mcp
lorekeeper setup  # auto-detects Claude Code, Cursor, Hermes
lorekeeper        # starts the MCP server
```

Then ask your agent:
> _"Remember that I prefer curl -vX GET for debugging."_

Next session:
> _"What's my preferred debug command?"_

It remembers.

## Tech stack

Python, SQLite + LanceDB (or ChromaDB), sentence-transformers, BM25, FastMCP. ~1.4GB for the embedding model. Apache 2.0 licensed.

---

**Links:**
- GitHub: https://github.com/Jessinra/Lorekeeper
- Docs: https://jessinra.github.io/Lorekeeper/
- PyPI: `pip install lorekeeper-mcp`