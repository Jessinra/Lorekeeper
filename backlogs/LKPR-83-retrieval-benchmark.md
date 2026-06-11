---
id: LKPR-83
title: Standalone retrieval algorithm benchmark
type: feature
sprint: unplanned
rice_score: ~
filed_by: Jason
filed_date: 2026-06-11
github_issue: 188
---

# [LKPR-83] Standalone retrieval algorithm benchmark

## Problem

We need a way to benchmark Lorekeeper's core retrieval algorithm (semantic vector search + BM25 keyword search → hybrid ranking) in isolation — without the MCP server, SQLite stores, or any app-level logic. This lets us:

- Compare weight configurations (w_semantic, w_keyword) on a standard dataset
- Measure latency per query
- Debug retrieval behavior without the app stack
- Produce comparable numbers for future algorithm improvements

The current test suite tests correctness/unit behavior, not retrieval quality on a standard benchmark.

## Solution

A standalone Python script at `scripts/benchmark_retrieval.py` that replicates the exact retrieval pipeline from `src/lorekeeper/services/`:

1. **Semantic**: sentence-transformers `all-MiniLM-L6-v2` → cosine similarity (brute force, same as LanceDB full scan would give)
2. **Keyword**: BM25 via `rank_bm25` with field boosts (`title×3 + description×2 + content×1`), top-hit normalized to 1.0
3. **Hybrid**: exact `hybrid_score()` formula — `w_sem·semantic + w_key·keyword` (memory_score and usage_count terms zeroed out since those need app-level data)

Runs against the **LongMemEval-S** dataset (ICLR 2025, 500 questions, ~48 sessions per question with `answer_session_ids` gold labels — downloaded from HuggingFace `xiaowu0162/longmemeval-cleaned`). Each question has known gold session IDs, so the metric is pure retrieval: did the right session appear in top-k? No LLM needed.

The same script also supports **LoCoMo** (`--dataset locomo`) for ablation/weight comparison, but LongMemEval-S is the primary dataset for comparable numbers.

A working prototype against LoCoMo is at `scripts/benchmark_retrieval.py` (filed alongside this ticket).

## Acceptance Criteria

- [ ] Script is self-contained — zero imports from Lorekeeper source (no MCP, no SQLite, no orchestrator)
- [ ] Replicates the exact same retrieval pipeline: same embedding model, same BM25 field boosts, same hybrid scoring formula
- [ ] Downloads both **LongMemEval-S** (primary) and LoCoMo (secondary) datasets automatically, caches locally
- [ ] For LongMemEval-S: ingests `haystack_sessions` as memories, evaluates by checking if any `answer_session_ids` appear in top-k results
- [ ] For LoCoMo: maintains the existing answer-text substring metric as a secondary signal
- [ ] Processes all 500 LongMemEval-S questions (or `--samples N` subset)
- [ ] Reports: per-sample recall@1/3/5/10 + MRR, aggregate across all questions with ±std
- [ ] Supports `--ablate` flag that sweeps weight combos (semantic-only, keyword-only, 50/50, default, etc.)
- [ ] Supports `--verbose` for per-query inspection
- [ ] Reports `--k` configurable top-k values (default: 1, 3, 5, 10)
- [ ] Reports per-category breakdown based on `question_type` (single-session, multi-session, temporal, knowledge-update, abstention)
- [ ] Runs from repo root: `uv run python scripts/benchmark_retrieval.py`
- [ ] Latency measurement: reports ms/query after each sample

## Non-goals (explicitly out of scope)

- No MCP server, SQLite stores, namespace filtering, memory score, usage_count, or decay factor — pure algorithm only
- No LLM-as-judge or answer generation — pure retrieval only: does the gold session appear in top-k?
- No integration with ProsusAI/MemEval framework (that can be a separate ticket)
- No CI integration (manual run only)

## Affected Files

**Backend:**

- `scripts/benchmark_retrieval.py` — the new standalone benchmark script

**Dashboard:**

- _none_

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] N/A — no code changes to the server
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

_None_

## Notes

LongMemEval-S (from `xiaowu0162/longmemeval-cleaned` on HuggingFace) has 500 questions with:

- `answer_session_ids` — gold session IDs that contain the answer
- `haystack_sessions` — full session content to search through
- `haystack_session_ids` — IDs of all searchable sessions
- `question_type` — single-session, multi-session, temporal, knowledge-update, abstention

The metric is: for each question, ingest all `haystack_sessions`, run retrieval, check if any `answer_session_ids` appear in the top-k results. This is identical to how agentmemory reports its 95.2% R@5.

LoCoMo is kept as a secondary dataset (`--dataset locomo`) because it has a different structure (conversations with QA pairs, no explicit session-level gold labels) — useful for weight ablation and debugging, not for comparable numbers.

Initial ablation results (all 10 samples):

| Config               | R@1  | MRR   |
| -------------------- | ---- | ----- |
| semantic-only        | 2.8% | 0.055 |
| keyword-only         | 7.5% | 0.101 |
| default (0.45/0.30)  | 7.4% | 0.107 |
| balanced (0.50/0.50) | 8.0% | 0.110 |

Hybrid always beats either signal alone. Balanced (50/50) slightly edges the default on this strict metric.
