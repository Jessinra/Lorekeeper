---
id: LKPR-70
title: Benchmark / Eval Script — retrieval quality + performance + end-to-end
type: enhancement
status: S:Proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: PM (Akane)
filed_date: 2026-06-08
github_issue: 162
---

## Problem

We don't have a repeatable way to measure Lorekeeper's retrieval quality or performance. When we make changes to the scoring formula, embedding strategy, or link pipeline, we can't tell if we regressed or improved. When we ship v2 beta, we'll want to show numbers — especially against the agentmemory benchmarks that buyers/competitors point to.

## Solution

Build an `scripts/eval/` directory with a benchmark suite modeled on agentmemory's methodology, adapted for Lorekeeper's architecture.

### Quality evaluation (retrieval)

Generate a synthetic internal dataset (like agentmemory's 240 observations, 30 sessions, 20 labeled queries with ground-truth relevance) and run:

- **Recall@K** (R@5, R@10, R@20) — fraction of relevant docs in top K
- **Precision@K** (P@5, P@10) — fraction of top K that are relevant
- **NDCG@10** — ranking quality
- **MRR** — position of first relevant result
- **Per-category breakdown**: exact match, semantic, cross-session, entity-based queries

Run across these configurations:

- BM25-only (our fallback path)
- Hybrid (BM25+vector, base config)
- Hybrid + links (BM25+vector+link boost)
- Built-in baseline (CLAUDE.md grep / BM25 no scoring)

### Scale evaluation (performance)

Ingest at increasing corpus sizes (240, 1k, 5k, 10k) and measure:

- **Index build time** (vector embedding + BM25 index)
- **Search latency** (p50/p95/p99 for BM25, hybrid, hybrid+links)
- **Storage costs** (SQLite, Chroma/LanceDB sizes)
- **Token consumption per query** (context injected vs. naive "load everything")
- **Cross-session retrieval** — can the system find info from sessions N sessions ago?

### End-to-end evaluation (task-driven)

Following agentmemory's E2E gap (they don't measure this either), and what Jason flagged as the harder problem:

- Define 5–10 canonical agent tasks that require memory (e.g. "remember the user's DB config preference across sessions", "find the deployment fix from last week")
- Run each task through a scripted agent loop that uses Lorekeeper MCP tools
- Score: did the agent produce the correct output? (binary pass/fail + subjective quality scale)
- Use an LLM judge (or manual, for v1) to assess answer quality
- Track pass@1 and pass@5 (did the right memory appear in the first attempt?)

### Reproducibility

All scripts, datasets, and results must be committed. One command to run:

```bash
uv run python scripts/eval/benchmark.py          # full suite
uv run python scripts/eval/benchmark.py --quality  # quality only
uv run python scripts/eval/benchmark.py --scale     # performance only
uv run python scripts/eval/benchmark.py --e2e       # end-to-end only
```

Results land in `scripts/eval/results/` with timestamps.

## Acceptance Criteria

- [ ] `scripts/eval/benchmark.py` runs quality, scale, and e2e modes
- [ ] Quality eval produces R@K, P@K, NDCG@K, MRR with per-category breakdown
- [ ] Scale eval produces latency histograms + storage costs at 4 corpus sizes
- [ ] E2E eval runs 5+ scripted agent tasks and scores pass/fail + quality
- [ ] Results are human-readable (markdown tables) and machine-readable (JSON)
- [ ] Dataset synthetic generator committed: `scripts/eval/generate_dataset.py`
- [ ] Documented in `docs/eval-script.md` with usage + interpretation guide
- [ ] Runs on fresh `git clone + setup.sh` with no extra deps beyond test extras

## Scope / Out of Scope

**In scope:**

- Synthetic dataset generation (matches agentmemory's approach for apples-to-apples comparison)
- Three evaluation modes: quality, scale, e2e
- Results output as markdown + JSON
- CI-compatible (`--quality` and `--scale` modes, < 5 min runtime)

**Out of scope (v1):**

- LongMemEval / LoCoMo / AMB integration (those are v2 benchmark ambitions)
- Multi-agent memory evaluation
- Regression dashboard / trending over time
- Real-user-data benchmarks (privacy, consent, etc.)

## Dependencies

- Non-blocking: tests pass, server runs, `scripts/smoke_test.py` green
- Needs: the existing `MemoryService` orchestrator API (doesn't need new tools)

## Required Updates

- [ ] README.md — add Benchmarks section pointing to `docs/eval-script.md`
- [ ] CLAUDE.md — add eval script to build order / tooling section
- [ ] Skills: `lorekeeper-dev` — add eval script usage
