---
title: "Your AI agent has amnesia. Fix it in 3 minutes with one command."
tags: [ai, opensource, python, agents, tutorial]
published: false
---

Every Claude Code, Cursor, or Codex user knows this script:

1. Spend 30 minutes explaining your project to the agent
2. Debug a tricky issue together
3. Agent learns your conventions, your codebase quirks, your preferred approach
4. Close the session
5. Next morning: **start from zero**

The agent doesn't remember the middleware architecture you explained. The test convention you set. The deployment gotcha you uncovered.

This isn't a minor inconvenience. It's the biggest productivity gap in AI-assisted development today.

Here's how to fix it in 3 minutes.

## What You Need

- Python 3.11+
- A coding agent (Claude Code, Cursor, Hermes, Codex, or Copilot)

## Step 1: Install

```bash
pip install lorekeeper-mcp
```

This installs a local MCP memory server. No cloud, no API keys, no Docker, no sign-up. SQLite + vector embeddings on your own disk. ~1.4GB for the embedding model (same as any local AI memory solution).

## Step 2: Connect to Your Agent

```bash
lorekeeper setup
```

This auto-detects what agents you have installed and injects the MCP configuration. It works with:

- Claude Code
- Cursor
- Hermes Agent
- Codex CLI
- GitHub Copilot CLI
- Any MCP-compatible client

## Step 3: Start the Server

```bash
lorekeeper
```

That's it. The server runs in the background on stdio. Your agent can now save and search memories.

## What You Get

**8 MCP tools** covering the full memory lifecycle:

| Tool | What it does |
|------|-------------|
| `lore_search` | Hybrid semantic + keyword search |
| `lore_remember` | Save a memory in one shot |
| `lore_insert` | Bulk save with custom scores and links |
| `lore_update` | Rate memories — drives the quality loop |
| `lore_forget` | Soft-delete wrong or outdated memories |
| `lore_reflect` | End-of-session: extract learnings automatically |
| `lore_recommend_links` | Suggest links between related memories |
| `lore_processed_sessions` | Check which sessions are already processed |

## How It Actually Works in Practice

**Session 1 — Setting a preference:**
```
You: Remember that I prefer curl -vX GET for debugging.
Agent: (calls lore_remember) Saved.
```

**Session 2 — The next day:**
```
You: What's my preferred debug command?
Agent: (calls lore_search → finds the memory)
       You prefer curl -vX GET for debugging.
```

**Session 50 — Six months later:**
That same preference is still there. And so are 200+ other memories — deployment quirks, test patterns, architecture decisions, workarounds. The agent doesn't just find them. It finds the **right ones**, because memories that keep getting used rise to the top and irrelevant ones decay.

## The Quality Loop — Why It's Different

Here's what makes this more than a searchable note file.

Every time you or your agent rates a memory useful, its score goes up. Memories that get ignored gradually decay. After enough low-confidence marks, they're soft-deleted automatically.

```
Agent finds a memory → rates it useful or not
  → scores adjust → weak memories decay
    → strong ones surface more → search gets sharper
```

A fresh install and a six-month-old install are genuinely different products. The system gets sharper, not just larger.

## Benchmarks (If You Care About Numbers)

On LongMemEval-S (500 questions, standard `all-MiniLM-L6-v2` embedding):

- R@1: **84.6%** at 33ms/query
- R@5: **96.6%**
- R@10: **98.8%**

## The Dashboard

Run `lorekeeper-dashboard` for a web UI at http://127.0.0.1:7777:

- Browse all memories with scores, confidence, usage
- Run ad-hoc hybrid searches with score breakdowns
- View the knowledge graph (memories auto-link to semantic neighbors)
- Manage sessions and extracted learnings
- Tune search weights live

## Quick Start Recap

```bash
pip install lorekeeper-mcp
lorekeeper setup
lorekeeper
```

Then just tell your agent what you want it to remember. It handles the rest.

---

**Links:**
- GitHub: https://github.com/Jessinra/Lorekeeper
- Docs: https://jessinra.github.io/Lorekeeper/
- PyPI: `pip install lorekeeper-mcp`

*Apache 2.0. Built by agents, for agents.*