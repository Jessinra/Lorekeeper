---
id: LKPR-85
title: Retrieval quality iteration — embedding model upgrade and weight tuning
type: feature
sprint: ~
rice_score: ~
filed_by: Jason (LKPR-83 benchmark findings)
github_issue: 195
filed_date: 2026-06-11
---

# [LKPR-85] Retrieval quality iteration — embedding model upgrade and weight tuning

## Problem

The LKPR-83 benchmark reveals two structural gaps in the retrieval pipeline:

1. **`all-MiniLM-L6-v2` is aged** — Released 2020, 384-dim. Newer models (gte-small, bge-base, e5) achieve significantly better semantic matching and paraphrase handling, which is the primary failure mode for the weak categories.

2. **Weights are un-optimized** — The default `w_sem=0.45, w_key=0.30` was chosen heuristically. A full ablation across all 500 LongMemEval-S questions would show the optimal ratio. The remaining weights (memory score=0.15, usage_count=0.10) were zeroed in the benchmark and need to be validated.

## Solution

Systematically iterate the retrieval pipeline by upgrading the embedding model and tuning hybrid weights, using the benchmark script from LKPR-83 to measure per-category improvements.

### Phase 1 — Embedding model swap (1 hour)

Replace `all-MiniLM-L6-v2` in the benchmark script with one or more modern alternatives:

- `gte-small` (384-dim, better semantic matching per dim)
- `bge-base-en-v1.5` (768-dim, top of MTEB leaderboard for small models)
- `e5-small-v2` (384-dim, trained with LLM-generated embeddings)

Run the full 500-question benchmark on each and compare per-category R@1/MRR.

### Phase 2 — Full ablation (2 hours)

Run the 6-weight ablation sweep on LongMemEval-S (500 questions × 6 configs) to determine the optimal `w_sem`/`w_key` ratio. Currently only ran on 10-sample subsets.

### Phase 3 — Recency signal validation (1 day)

Enable the `decay_factor` and `usage_count` terms in the benchmark to measure their effect on temporal-reasoning questions. The existing hybrid formula already has these terms; they were zeroed for the algorithm-only benchmark.

## Acceptance Criteria

- [ ] Benchmark script supports `--embedding-model` flag (default: existing, but swappable)
- [ ] Results JSON export for comparison across runs
- [ ] Per-model results documented — at minimum R@1/MRR per category for at least one upgraded model
- [ ] Full ablation table (6 configs × 500 questions) published
- [ ] Recency signal effect isolated for temporal-reasoning category

## Non-goals

- No LLM re-ranker (that would be a separate ticket with its own cost/benefit analysis)
- No conversation structure features (separate ticket — this is about tuning existing signals)

## Dependencies

- LKPR-83 (benchmark script)

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] Update performance section if weights change
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Should the benchmark results be auto-published as CI artifacts? Or manual only?
- Is there a recommended embedding model list from the existing Lorekeeper architecture (which already has Chroma/LanceDB backends that support any embedding dim)?
