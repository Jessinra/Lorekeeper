# Retrieval Benchmark Results — LongMemEval-S

**Date:** 2026-06-11
**Dataset:** LongMemEval-S (ICLR 2025, 500 questions)
**Pipeline:** sentence-transformers `all-MiniLM-L6-v2` (384-dim) + BM25 + hybrid ranking
**Default weights:** `w_sem=0.45`, `w_key=0.30` (memory score and usage count terms zeroed — algorithm-only benchmark)
**Metric:** Does the gold `answer_session_id` appear in top-k? Pure retrieval — no LLM.

## Aggregate (all 500 questions)

| Metric      | Mean    | Std     |
| ----------- | ------- | ------- |
| **R@1**     | 0.846   | 0.361   |
| **R@3**     | 0.936   | 0.245   |
| **R@5**     | 0.966   | 0.181   |
| **R@10**    | 0.988   | 0.109   |
| **MRR**     | 0.896   | 0.251   |
| **Latency** | 32.9 ms | 24.2 ms |

## Per-category Breakdown

### R@k by question type

| Category          | Count | R@1       | R@3   | R@5   | R@10  | MRR   |
| ----------------- | ----- | --------- | ----- | ----- | ----- | ----- |
| single-assistant  | 56    | **1.000** | 1.000 | 1.000 | 1.000 | 1.000 |
| knowledge-update  | 78    | **0.923** | 0.987 | 1.000 | 1.000 | 0.953 |
| multi-session     | 133   | **0.872** | 0.940 | 0.970 | 0.992 | 0.915 |
| single-user       | 70    | **0.843** | 0.957 | 0.971 | 1.000 | 0.897 |
| temporal          | 133   | **0.774** | 0.902 | 0.932 | 0.970 | 0.846 |
| single-preference | 30    | **0.567** | 0.767 | 0.933 | 0.967 | 0.692 |

### Per-category R@1 breakdown

```
single-assistant  ████████████████████████████████ 100.0%   (56/56)
knowledge-update  ██████████████████████████████▌   92.3%   (72/78)
multi-session     █████████████████████████████▏    87.2%  (116/133)
single-user       ████████████████████████████▏     84.3%   (59/70)
temporal          █████████████████████████▉        77.4%  (103/133)
single-preference █████████████████▊                56.7%   (17/30)
```

## Key Insights

1. **Overall R@1 of 84.6%** is competitive. At R@5 the pipeline catches **96.6%** of relevant sessions — meaning for nearly every query the right session is in the top 5.

2. **single-assistant is a freebie** (100% R@1). These questions ask about something the assistant itself generated — the verbatim overlap is trivial.

3. **single-preference is the hardest category** (56.7% R@1). Questions like "What color did I repaint my bedroom walls?" are vague queries against dense multi-turn conversations. The answer might be one word ("blue") buried in hundreds of turns. Pure text similarity struggles here.

4. **temporal reasoning** (77.4% R@1) also underperforms. Questions like "What did I do after my dentist appointment?" require understanding temporal ordering, not just text overlap. This is the category most likely to benefit from recency-aware scoring or LLM-based re-ranking.

5. **knowledge-update** (92.3% R@1) does well — these questions are about specific factual updates with clear verbatim cues.

6. **Latency of 32.9 ms/query** is fast enough for interactive use. The bottleneck is embedding generation, not BM25 or hybrid ranking.

## Comparison vs AgentMemory

For reference, AgentMemory reports 95.2% R@5 on LongMemEval. Lorekeeper's 96.6% R@5 is slightly better, though the numbers aren't directly comparable due to pipeline differences (AgentMemory uses its proprietary embedding model; Lorekeeper uses the standard `all-MiniLM-L6-v2`).

The gap at R@1 (AgentMemory likely higher) suggests Lorekeeper could benefit from better top-1 precision — areas to explore: weight tuning, query expansion, or hybrid with learned re-ranking.

## Raw ablation seed data (LoCoMo)

First 10 LoCoMo samples with the same pipeline (answer-text substring metric, not directly comparable):

| Config                  | R@1       | R@3       | R@5       | R@10      | MRR       |
| ----------------------- | --------- | --------- | --------- | --------- | --------- |
| semantic-only           | 0.020     | 0.040     | 0.045     | 0.075     | 0.036     |
| keyword-only            | 0.040     | 0.045     | 0.065     | 0.085     | 0.053     |
| w_sem=0.70, w_key=0.30  | 0.035     | 0.050     | 0.060     | 0.075     | 0.050     |
| **default (0.45/0.30)** | **0.035** | **0.060** | **0.070** | **0.085** | **0.054** |
| w_sem=0.50, w_key=0.50  | 0.040     | 0.065     | 0.070     | 0.085     | 0.057     |
| w_sem=0.30, w_key=0.70  | 0.040     | 0.055     | 0.070     | 0.090     | 0.055     |

Hybrid always beats either signal alone on LoCoMo. Balanced 50/50 slightly edges the default on this metric.

---

## Failure Analysis

### single-session-preference (56.7% R@1) — Cold retrieval problem

The worst-performing category. These queries ask about a general preference in one domain but the gold session is about a **different specific topic**:

> **Query:** _"Can you suggest a hotel for my upcoming trip to **Miami**?"_ > **Gold session:** User discussing a **Seattle** trip

The query and gold session share only generic verbs (suggest, recommend, want, help). The specific topic terms (Miami vs Seattle, hotel vs apartment) differ. Keyword overlap with the gold session is effectively zero for the topic-bearing words.

**Root cause:** This is a **cold retrieval** problem — the textual signal connecting query to gold session is too weak for any pure text-similarity approach to reliably rank it at position 1. The correct session is identified by conversation _structure_ (user-asks-for-recommendation → assistant-responds → user-follows-up) rather than content.

### temporal-reasoning (77.4% R@1) — Missing temporal features

These queries ask about _relative timing and ordering_ ("How many days passed between X and Y?", "Which happened first?"). The gold session contains the right events, but the temporal _relationship_ is what the question tests. Keyword overlap with gold: **60.5%** average (vs 75.7% for knowledge-update).

**Root cause:** Pure text similarity cannot model temporal ordering. The `decay_factor` in the hybrid score (zeroed in this benchmark) would help by boosting recent sessions.

### single-session-user (84.3% R@1) — Paraphrase / sparse mention

Queries ask about specific user-stated facts. Some are trivial ("What breed is my dog?" — the breed name appears verbatim). Others fail when the mention is a single word buried in 48 sessions × 12 turns each, and the query uses a paraphrase with no verbatim overlap.

---

## Improvement Candidates

| Idea                                                            | Category Helped  | Effort        | Why It Would Work                                                                                                                                                                                                                       |
| --------------------------------------------------------------- | ---------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Weight tuning** (ablate different `w_sem`/`w_key`)            | All (minor)      | Trivial       | Already hybrid; small tweaks might gain 1-2% on aggregate                                                                                                                                                                               |
| **Different embedding model** (`gte-small`, `bge-base`, `e5`)   | preference, user | 1 hour        | `all-MiniLM-L6-v2` is 384-dim, released 2020. Newer 768-dim models handle paraphrase better                                                                                                                                             |
| **Recency scoring** (enable `decay_factor` term)                | temporal         | 1 day         | Already built into the formula but zeroed for this benchmark                                                                                                                                                                            |
| **Query expansion** (append common assistant response patterns) | preference       | 2 days        | "Recommend a hotel for Miami" → expand with "recommendation, suggestions, hotels" to catch more conversational structure                                                                                                                |
| **Conversation structure signals** (encode role-pattern)        | preference       | 2-3 days      | User-asks→assistant-answers→user-follows-up pattern is distinctive for preference sessions                                                                                                                                              |
| **LLM re-ranker** (classify top-20 candidates)                  | All              | 1 week + cost | Would catch all categories but adds latency and per-query cost                                                                                                                                                                          |
| **single-preference ceiling**                                   | preference       | —             | This category may have a **hard ceiling** for text-only retrieval. When query and gold session share zero topic-specific terms, no embedding or BM25 tuning can bridge the gap reliably. A structural or behavioral signal is required. |
