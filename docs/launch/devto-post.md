# Self-Improving Memory for AI Agents: Lorekeeper v0.3.0 Beta

Every AI coding session starts blank. You re-explain context, re-state preferences, re-teach patterns — every single time.

Files like `CLAUDE.md` and `.cursorrules` help, but they're hand-maintained. Cloud memory services work, but your data leaves your machine. Libraries are powerful, but you're writing the integration yourself.

**Lorekeeper** is a different approach: a local MCP memory server you `pip install` once. It connects to your agents (Claude Code, Cursor, Hermes, Codex, Copilot) and stores memories on your own disk.

The difference? It gets **better with use.**

## The Feedback Loop

Most memory stores are buckets. You put memories in, you search for them later.

Lorekeeper has a quality loop:

```
Agent finds a memory → rates it useful or not
  → scores adjust automatically
    → weak memories decay
      → strong ones surface more
        → search gets sharper
```

A six-month-old install is genuinely different from a fresh one. The memories that help you keep rising; the noise fades away.

## Benchmarks

On LongMemEval-S (ICLR 2025, 500 questions), running the standard `all-MiniLM-L6-v2` embedding model:

| Metric | Value | Latency |
|--------|-------|---------|
| R@1 | **84.6%** | 33 ms |
| R@5 | **96.6%** | — |
| R@10 | **98.8%** | — |

For comparison, AgentMemory reports 95.2% R@5 on the same benchmark. Lorekeeper's 96.6% R@5 is slightly higher — using the same open-source embedding model, not proprietary ones.

## What Ships in v0.3.0

- **Hybrid search** — semantic vectors + BM25 keyword + time-decay + usage frequency + memory score, all ranked by a weighted formula
- **Auto-linking** — new memories link to their closest semantic neighbor. A knowledge graph forms without effort
- **Duplicate detection** — near-identical content is blocked automatically
- **Dashboard** — full web UI to browse, search, edit, manage memories
- **Namespaces** — multiple agents share one store with isolated scopes
- **8 MCP tools** covering the full memory lifecycle: search, remember, insert, update, forget, reflect, link recommendations, session tracking

## Quick Start

```bash
pip install lorekeeper-mcp
lorekeeper setup   # auto-detects Claude Code, Cursor, Hermes
lorekeeper         # starts the MCP server
```

Then ask your agent:
> _"Remember that I prefer curl -vX GET for debugging."_

Next session:
> _"What's my preferred debug command?"_

It remembers.

## Why Open Source Matters Here

Lorekeeper is itself built **by AI agents** — Claude Code, Hermes, and Copilot. Every tool schema, return type, and workflow was shaped by agents using it daily. When search returned noise, we tuned the weights. When something was annoying, we changed it.

The repo is a working demo of what it does: agents building better agents, with memory that compounds.

## Links

- **GitHub:** https://github.com/Jessinra/Lorekeeper
- **Docs:** https://jessinra.github.io/Lorekeeper/
- **Install:** `pip install lorekeeper-mcp`

---

*Apache 2.0. Built by agents, for agents.*