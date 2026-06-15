---
title: "We built an AI memory server using AI agents. The irony writes itself."
tags: [ai, opensource, python, agents, showdev]
published: false
---

**How building with Claude Code forced us to build memory for Claude Code — and why the agent-written commit message "this code works but i have no idea why" finally convinced us we needed it.**

Eight weeks ago, I started a project with a simple rule:

Every line of code would be written by AI agents. Claude Code, Hermes, Copilot — whatever could do the job. I'd review, merge, and steer. They'd build.

The first week was magic. I got more done in 5 days than in the previous month. New features, cleaner architecture, working tests.

By week three, the wheels came off.

## The Amnesia Problem

Every morning, I'd start a new agent session and spend 30 minutes re-explaining context. The project structure. The weird authentication flow. Why we chose LanceDB over Chroma. The commit message convention.

My agents had built an entire codebase. They just couldn't remember why they made the decisions they did.

Session logs piled up. The `.claude/projects/` directory grew. But the agent started each conversation blank. It would make the same mistakes, propose the same rejected approaches, ask the same questions.

I was watching AI run in circles.

## The Accidental Solution

So I did the most on-brand thing possible: I asked an agent to build a memory server for agents.

The requirements were simple:
- One command install. No Docker, no cloud, no API keys.
- Agents could save what they learned and search it later.
- The system got better the more you used it — not just bigger.

Three weeks later, **Lorekeeper** was running in production. On itself.

## The Feedback Loop

Most memory stores are buckets. You put memories in, you search later. Over time, everything becomes noise.

Lorekeeper has a different shape. Every time an agent uses a memory, it rates it:

```
Agent finds a memory → rates it useful or not
  → scores adjust → weak memories decay
    → strong ones surface more → search gets sharper
```

Bad memories get soft-deleted automatically. Good ones rise to the top. A memory from week 1 that keeps proving useful still surfaces. A dead-end approach from last Tuesday quietly fades.

I didn't design this loop. The agents did. They kept surfacing the same useful memories, so we built a system that amplifies that pattern. The product is what it is because the agents that use it every day forced us to make it better.

## The Numbers

On the LongMemEval-S benchmark:

- R@1: **84.6%** (33ms)
- R@5: **96.6%**
- R@10: **98.8%**

Built with the same `all-MiniLM-L6-v2` model every open-source project uses. No proprietary magic.

## What It Ships

- **Hybrid search** — semantic vectors + BM25 + time-decay + usage + score
- **Auto-linking** — memories link to their nearest semantic neighbor. A graph forms without effort
- **Dashboard** — browse, search, edit, delete. 7 tabs
- **8 MCP tools** — search, remember, insert, update, forget, reflect, link, session tracking

Works with Claude Code, Cursor, Hermes, Codex, Copilot — any MCP-compatible agent.

## The Honest Part

Memory is the hardest unsolved problem in the AI agent space. We haven't solved it either. What we built is the first layer — a system that remembers what it learned and gets better at finding it.

The next layer (team memory, provenance, conflict resolution) is already on the roadmap. But for a solo developer or a small team running coding agents, this changes the daily experience from "start from zero" to "pick up where you left off."

## Try It

```bash
pip install lorekeeper-mcp
lorekeeper setup
lorekeeper
```

Then tell your agent: *"Remember that I prefer curl -vX GET for debugging."*

Tomorrow, ask it: *"What's my preferred debug command?"*

It remembers.

---

*The code in this post was reviewed by an AI agent. I asked it to check for errors. It used Lorekeeper to remember our code review conventions first.*