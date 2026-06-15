---
title: "I spent 3 months watching AI agents forget everything. So I built a memory loop."
tags: [ai, opensource, python, agents, showdev]
published: false
---

Three months ago, I committed to a rule: every line of code would be written by AI agents.

Claude Code for backend, Hermes for planning, Cursor for frontend. I'd steer. They'd build.

**Week one was euphoric.** Features I'd have spent days on were done in hours. The code was clean. Tests passed. I felt like I'd discovered a productivity cheat code.

**Week three was painful.** Every morning, 30 minutes of re-explaining. The project structure. The auth flow. Why we chose that ORM. The commit convention we agreed on.

My agents had built an entire codebase. They just couldn't remember *why* they made the decisions they did.

**Week six was the breaking point.** I watched Claude Code propose the same rejected API design I'd killed three weeks earlier — in detail, with citations to the old conversation. It had the information. It just couldn't connect it to the present.

The session transcripts were all there on disk. Thousands of lines of conversation history. The agent was drowning in data it couldn't use.

## What I Learned About Agent Memory

After digging into the problem, I found three root causes:

**1. Context files are too brittle.** CLAUDE.md and .cursorrules work for the first few sessions. But they're hand-maintained. They don't auto-decay stale information. They don't deduplicate. By session 20, they're contradictory messes.

**2. Vector search alone isn't enough.** Pure semantic similarity can't distinguish "I fixed this bug yesterday" from "I found this interesting three months ago." Recency, frequency of use, and user ratings all matter — but almost no memory system combines them.

**3. No feedback loop.** Every memory system stores and retrieves. None of them get better at finding what's useful. The first memory you save and the 500th look the same to the search algorithm.

## What I Built

**Lorekeeper** is a local MCP memory server with one difference: a quality loop.

```
Agent uses a memory → rates it useful or not
  → scores adjust → weak memories decay
    → strong ones surface more → search gets sharper
```

The scoring is a weighted hybrid:

- **45% semantic similarity** (what does it mean?)
- **30% keyword overlap** (what words match?)
- **15% memory score** (how useful has it been?)
- **10% usage frequency** (how often is it accessed?)
- **Time decay** (old memories gradually lower)

The result: memories that help you keep rising. Noise fades. A six-month-old install is genuinely sharper than a fresh one.

**96.6% R@5 on LongMemEval-S** — running the same `all-MiniLM-L6-v2` embedding model any open-source project uses. No proprietary magic.

## The Meta Part

Building Lorekeeper *with* agents was the ultimate test. Every time search returned bad results, we tuned the weights. Every time a tool was annoying to use, we changed the schema.

The product is what it is because the agents that depend on it helped build it.

## One Command

```bash
pip install lorekeeper-mcp && lorekeeper setup && lorekeeper
```

Then tell your agent: *"Remember that I prefer curl -vX GET for debugging."*

Tomorrow, ask it: *"What's my preferred debug command?"*

It remembers. And next week, it'll be even better at finding the right answer.

---

**GitHub:** https://github.com/Jessinra/Lorekeeper
**Docs:** https://jessinra.github.io/Lorekeeper/

*Apache 2.0. Built by agents, for agents.*