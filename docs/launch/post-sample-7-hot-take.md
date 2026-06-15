---
title: "99% of AI agent memory servers are just search. That's not memory."
tags: [ai, programming, architecture, python, discuss]
published: false
---

I've tested every open-source AI agent memory server I could find.

There are dozens of them now — more every week. The READMEs all say the same thing: "persistent memory for your AI agent," "never start from zero," "cross-session recall."

But when I actually ran them, almost all of them had the same shape:

**A bucket you put things into and search later.**

That's not memory. That's search.

## Real Memory Requires a Feedback Loop

Human memory doesn't work like a database query. We don't recall everything related to a topic equally — we recall what *matters*. What we've confirmed, what we've used recently, what's proven useful repeatedly.

Every agent memory server I tested stores everything with equal weight. The first fact you save and the 500th one look identical to the search algorithm. Fresh facts, stale facts, useful facts, dead ends — all equally retrievable, all equally noisy.

This isn't a minor design choice. It's the difference between a growing haystack and a system that actually gets sharper.

## The Metrics That Matter

I benchmarked several systems on LongMemEval-S (500 questions, ICLR 2025). Raw R@5 numbers were similar — most hit 90-96% — because that benchmark tests *retrieval*, not *curation*.

The gap shows up in real use after 50+ sessions. Questions like:

- "What did we decide about the database migration approach?"
- "What's the deployment gotcha I keep hitting?"
- "Which approach did we reject last month?"

These aren't semantic similarity questions. They're questions about *what matters most right now*. And no amount of vector search can answer them without usage data and temporal weighting.

## What I Look For Now

When I evaluate a memory server, I check for three things:

**1. Score drift.** Can a memory's relevance change over time? If a memory is confirmed useful 10 times, does it rank higher than one confirmed once?

**2. Temporal decay.** Does the system distinguish "last week" from "three months ago"? The most important memory from last month is more relevant than a marginally related one from yesterday.

**3. Soft delete.** When a memory proves consistently unhelpful, does it fade automatically — or does it keep cluttering results forever?

Out of a dozen systems I tested, **exactly one** had all three: Lorekeeper.

I didn't build it — the agents building it did. The quality loop was extracted from how the development team (Claude Code, Hermes, Copilot) actually worked. They kept surfacing the same useful memories, so the system learned to amplify that pattern.

## The Honest Part

Memory for AI agents is still the hardest unsolved problem in the space. What I'm describing — a feedback loop with score drift, temporal decay, and soft delete — is layer 1. Layer 2 (team signal aggregation, provenance, conflict resolution) barely exists anywhere.

But layer 1 is enough to change the daily experience from "start from zero" to "pick up where you left off." And that's a bigger leap than most people realize.

**Test it yourself:**

```bash
pip install lorekeeper-mcp && lorekeeper setup && lorekeeper
```

Then use it for a month. Compare week 1 results to week 4. The difference is the feedback loop.

---

**GitHub:** https://github.com/Jessinra/Lorekeeper
**Docs:** https://jessinra.github.io/Lorekeeper/

*Apache 2.0. Built by agents, for agents.*