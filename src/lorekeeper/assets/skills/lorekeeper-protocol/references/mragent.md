# MRAgent — Memory is Reconstructed, Not Retrieved

**Paper**: _"Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents"_
**Authors**: Shuo Ji, Yibo Li, Bryan Hooi (National University of Singapore)
**Venue**: ICML 2026
**arXiv**: [2606.06036](https://arxiv.org/abs/2606.06036)

---

## Core Thesis

Current memory-augmented agents use a **static retrieve-then-reason** pipeline — search once, then reason with results. This is rigid and prevents adapting memory access to intermediate evidence discovered during reasoning.

MRAgent flips this: **reason-to-retrieve**, not retrieve-then-reason. Memory access is an active, multi-step reconstruction process guided by the LLM's own reasoning.

---

## Key Components

### 1. Cue-Tag-Content Graph

Three-layer memory structure:

| Layer       | Role                                                                 |
| ----------- | -------------------------------------------------------------------- |
| **Cue**     | Fine-grained query/keyword. What triggers a memory lookup.           |
| **Tag**     | Associative semantic bridge. Connects cues to content via relations. |
| **Content** | The actual memory (episodic or semantic).                            |

Tags are the key innovation — they're not just categories, they're **semantic bridges** that let the LLM reason about which retrieval paths are promising before diving into full content.

### 2. Active Reconstruction Mechanism

Instead of one-shot retrieval, an iterative loop:

```
REASON over current state → INFER new cues → TRAVERSE graph via tags/links
→ PRUNE irrelevant branches → REASON again → repeat until converged
```

This maps to Lorekeeper's `lore_search` → read → `lore_update(feedback)` → follow links → re-search pattern.

### 3. Pruning Strategy

Without pruning, iterative graph expansion explodes combinatorially. MRAgent:

- Prunes branches where intermediate evidence contradicts the current query
- Limits exploration depth (capped at 8 traversal turns per query in their setup)
- Uses LLM reasoning to score which paths have the highest information gain

---

## Results

- **LoCoMo benchmark**: up to **23% improvement** over strong baselines
- **LongMemEval**: consistent gains across all evaluation settings
- **Token cost**: significantly _less_ than static retrieval baselines (pruning prevents expensive irrelevant fetches)
- **Runtime**: faster than baselines despite the iterative loop (targeted searches beat broad retrievals)

---

## Lorekeeper Protocol Mapping

| MRAgent Concept            | Lorekeeper Equivalent                                        |
| -------------------------- | ------------------------------------------------------------ |
| Cue-Tag-Content graph      | Memories + link types (`references`, `depends_on`, etc.)     |
| Active reconstruction      | Phase 1.5: search → reason → link-traverse → prune → repeat  |
| Associative tags           | `relation_type` in `lore_insert` links                       |
| Pruning dead ends          | `lore_update(useful=false)` to deprioritize irrelevant paths |
| Reason-guided re-search    | Infer new cues from what was read, then `lore_search` again  |
| Information gain threshold | Break when 2 consecutive iterations yield no new results     |

---

## Limitations (from the paper)

1. **Cost scales with depth** — deep traversals cost more than shallow ones. The protocol caps iterations at 2–3 for practical use.
2. **No memory consolidation** — MRAgent builds a static graph; it doesn't update or merge memories over time. Phase 4 (health maintenance) fills this gap in Lorekeeper.
