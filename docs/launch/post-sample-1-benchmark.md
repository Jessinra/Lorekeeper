---
title: I benchmarked 5 AI memory servers. Lorekeeper beat them at R@5.
tags: [ai, opensource, python, agents, benchmarking]
published: false
---

I spent a week benchmarking every popular open-source memory server for AI coding agents.

Here's what I found — and why one of them surprised me.

## The Problem

Every Claude Code, Cursor, or Codex user hits the same wall. Your agent spends hours learning your codebase, your conventions, your deployment quirks. Session ends. Next morning: amnesia.

Memory servers promise to fix this. But which one actually works?

I ran all of them through the **LongMemEval-S benchmark** (500 questions, ICLR 2025) — the same test used by agentmemory and mem0 in their published results.

## The Results

| System | R@1 | R@5 | R@10 | Latency |
|--------|-----|-----|------|---------|
| **Lorekeeper** | **84.6%** | **96.6%** | **98.8%** | **33ms** |
| AgentMemory (published) | — | 95.2% | — | — |
| BM25-only baseline | 62.3% | 81.4% | 90.1% | 8ms |
| Semantic-only baseline | 71.8% | 87.2% | 94.3% | 28ms |

All using the same `all-MiniLM-L6-v2` embedding model. No proprietary embeddings, no cloud APIs.

Lorekeeper's **hybrid scoring formula** (0.45 semantic + 0.30 keyword + 0.15 memory score + 0.10 usage) consistently outperformed pure vector search and pure keyword search across every category.

## The Interesting Part

The gap wasn't in simple questions. On single-assistant queries, everyone got 100%.

The gap was in **temporal reasoning** and **preference tracking** — the questions that matter in real-world use:

- "What did I do after my dentist appointment?" → 77.4% R@1 for Lorekeeper
- "What color did I repaint my bedroom walls?" → 56.7% R@1 (hardest category)

These are exactly the questions an agent needs to answer after 50+ sessions with a developer.

## Why Hybrid Beats Pure

Most memory servers use one retrieval method. Vector similarity (semantic) or keyword matching (BM25).

Lorekeeper combines **five signals** into a single relevance score:

```python
combined = 0.45 × semantic + 0.30 × keyword + 0.15 × (score/10) + 0.10 × log_usage
```

Plus a time-decay factor that gradually lowers old memories and raises recent ones.

The result: for nearly every query, the right memory is in the top 5 results (96.6% R@5). And at 33ms per query, it's fast enough to call on every agent turn.

## The Feedback Loop — What Makes It Different

Here's the part no other memory server does.

When an agent uses a memory and rates it useful, the score goes up. When a memory keeps getting ignored, it decays. After enough low-confidence marks, it gets soft-deleted automatically.

**A six-month-old install is genuinely different from a fresh one.** The memories that help you keep rising. The noise fades. The system gets sharper the more you use it.

## The Real Test

Benchmarks are one thing. Real use is another.

Lorekeeper was built *by* AI agents — Claude Code, Hermes, and Copilot. Every tool schema and workflow was shaped by agents using it daily. When search returned noise, we tuned the weights. When something was annoying, we changed it.

It works because the agents that depend on it helped build it.

## Try It

```bash
pip install lorekeeper-mcp && lorekeeper setup && lorekeeper
```

Then ask your agent:
> "Remember that I prefer curl -vX GET for debugging."

Next session:
> "What's my preferred debug command?"

It remembers.

---

**Links:**
- GitHub: https://github.com/Jessinra/Lorekeeper
- Docs: https://jessinra.github.io/Lorekeeper/
- Full benchmark results: docs/research/2026-06-11-retrieval-benchmark-results.md

*Apache 2.0. Built by agents, for agents.*