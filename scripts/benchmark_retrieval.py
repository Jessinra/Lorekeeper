#!/usr/bin/env python3
"""Benchmark Lorekeeper's hybrid retrieval algorithm alone — no MCP server, no SQLite stores.

Replicates the exact pipeline from src/lorekeeper/services/:
  - embedding: sentence-transformers all-MiniLM-L6-v2 (384-dim)
  - semantic: cosine similarity (brute force, same as LanceDB full scan)
  - keyword: BM25 with field boosts (titlex3 + descriptionx2 + contentx1)
  - hybrid: w_sem * semantic + w_key * keyword

Two datasets:
  - LongMemEval-S (primary, ICLR 2025): 500 questions with gold session IDs
  - LoCoMo (secondary): 10 synthetic conversations with QA pairs

Usage:
  uv run python scripts/benchmark_retrieval.py
  uv run python scripts/benchmark_retrieval.py --samples 2 --verbose
  uv run python scripts/benchmark_retrieval.py --ablate
  uv run python scripts/benchmark_retrieval.py --dataset locomo
  uv run python scripts/benchmark_retrieval.py --semantic-only
"""

import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

LOCOMO_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORY_NAMES_LM = {
    "single_session": "single-session",
    "multi_session": "multi-session",
    "temporal": "temporal",
    "knowledge_update": "knowledge-update",
    "abstention": "abstention",
    "single-session-user": "single-user",
    "single-session-assistant": "single-assistant",
    "single-session-preference": "single-preference",
    "multi-session": "multi-session",
    "temporal-reasoning": "temporal",
    "knowledge-update": "knowledge-update",
}
CATEGORY_NAMES_LOCOMO = {1: "Factual", 2: "Temporal", 3: "Inferential",
                         4: "Multi-hop", 5: "Adversarial"}

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Algorithm (exact replica of Lorekeeper internals) ──────────────────────


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def bm25_scores(corpus_tokens: list[list[str]], query_tokens: list[str],
                k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    n_docs = len(corpus_tokens)
    if n_docs == 0 or not query_tokens:
        return np.zeros(n_docs)
    doc_lens = np.array([len(toks) for toks in corpus_tokens], dtype=float)
    avgdl = float(doc_lens.mean()) if len(doc_lens) else 1.0
    idf = {}
    for qt in query_tokens:
        df = sum(1 for toks in corpus_tokens if qt in toks)
        idf[qt] = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
    scores = np.zeros(n_docs)
    for i, toks in enumerate(corpus_tokens):
        tf_counts = {t: toks.count(t) for t in query_tokens}
        for qt in query_tokens:
            tf = tf_counts.get(qt, 0)
            if tf > 0:
                scores[i] += idf.get(qt, 0) * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * doc_lens[i] / avgdl)
                )
    return scores


def keyword_search_normalized(corpus_tokens: list[list[str]], ids: list[str],
                              query: str) -> dict[str, float]:
    """Replicates KeywordIndex.search_normalized — top-hit normalized to 1.0."""
    qtokens = _tokenize(query)
    raw = bm25_scores(corpus_tokens, qtokens)
    max_val = float(raw.max()) if len(raw) and raw.max() > 0 else 0.0
    if max_val <= 0:
        return {}
    return {ids[i]: float(raw[i]) / max_val for i in range(len(ids)) if raw[i] > 0}


def hybrid_score(semantic: float, keyword: float, w_sem=0.45, w_key=0.30) -> float:
    """Pure retrieval portion — no memory-score or usage terms (those need app-level data)."""
    return w_sem * semantic + w_key * keyword


# ── LongMemEval-S data ─────────────────────────────────────────────────────


def download_longmemeval_s() -> list[dict]:
    """Download LongMemEval-S dataset from HuggingFace via datasets library (streaming)."""
    path = DATA_DIR / "longmemeval_s.json"
    if path.exists():
        print(f"[data] LongMemEval-S loaded from cache ({path})")
        return json.loads(path.read_text())

    print("[data] Downloading LongMemEval-S from HuggingFace (streaming)...")
    try:
        from datasets import load_dataset  # type: ignore[import-untyped]
        ds = load_dataset(
            "xiaowu0162/longmemeval-cleaned",
            split="longmemeval_s_cleaned",
            streaming=True,
        )
        data = list(ds)
        path.write_text(json.dumps(data, indent=2))
        print(f"[data] Cached {len(data)} questions to {path}")
    except ImportError:
        print("[error] 'datasets' not installed. Install: uv add datasets")
        print("[error] Falling back to LoCoMo-only mode.")
        return []
    except Exception as e:
        print(f"[error] Failed to load LongMemEval-S: {e}")
        print("[error] Falling back to LoCoMo-only mode.")
        return []

    print(f"[data] LongMemEval-S loaded: {len(data)} questions")
    return data


def ingest_longmemeval_question(question: dict) -> tuple[list[str], list[str], list[list[str]]]:
    """Ingest haystack_sessions into memory corpus.

    LongMemEval-S structure:
      - haystack_sessions: list of sessions, each is a list of JSON-string turns
        e.g. [['{\"role\":\"user\",\"content\":\"...\"}',
      - haystack_session_ids: str session IDs, parallel to haystack_sessions

    Returns (memory_ids, memory_texts, boost_tokens).
    """
    sessions = question.get("haystack_sessions", [])
    session_ids = question.get("haystack_session_ids", [])

    ids: list[str] = []
    texts: list[str] = []
    boost_tokens: list[list[str]] = []

    for idx, sess in enumerate(sessions):
        sid = session_ids[idx] if idx < len(session_ids) else f"s_{idx}"
        ids.append(sid)

        if not isinstance(sess, list):
            continue

        full_text = ""
        speaker_count: dict[str, int] = {}
        for turn_raw in sess:
            if isinstance(turn_raw, str):
                try:
                    turn = json.loads(turn_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            elif isinstance(turn_raw, dict):
                turn = turn_raw
            else:
                continue

            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            speaker_count[role] = speaker_count.get(role, 0) + 1
            full_text += content + " "

        texts.append(full_text.strip())

        # Build boost tokens: role×3 + text×1 (no title/description for LongMemEval-S)
        top_role = max(speaker_count, key=lambda r: speaker_count[r]) if speaker_count else "user"
        tokens = _tokenize(top_role) * 3 + _tokenize(full_text)
        boost_tokens.append(tokens)

    return ids, texts, boost_tokens


def evaluate_longmemeval(
    question: dict, model: Any,
    memory_ids: list[str], corpus_tokens: list[list[str]], embeddings: np.ndarray,
    k_vals: list[int], w_sem: float, w_key: float, verbose: bool,
) -> dict:
    """Evaluate one LongMemEval-S question.

    Metric: did any gold session ID appear in top-k?
    """
    query = question.get("question", "")
    gold_ids: list[str] = question.get("answer_session_ids", [])
    qtype = question.get("question_type", "unknown")

    t0 = time.perf_counter()

    # 1) Semantic: embed query, cosine similarity → top 200
    q_vec = model.encode(query, normalize_embeddings=True).astype(np.float32)
    cos_sims = embeddings @ q_vec
    sem_n = max(0, min(200, len(cos_sims) - 1))
    sem_idx = np.argpartition(-cos_sims, sem_n)[:sem_n]
    order = np.argsort(-cos_sims[sem_idx])
    sem_idx = sem_idx[order]
    sem_hits = {memory_ids[idx]: float(cos_sims[idx]) for idx in sem_idx}

    # 2) BM25 keyword (top-hit normalized)
    kw_hits = keyword_search_normalized(corpus_tokens, memory_ids, query)

    # 3) Hybrid ranking
    cand = set(sem_hits) | set(kw_hits)
    scored = [(lid, hybrid_score(sem_hits.get(lid, 0.0), kw_hits.get(lid, 0.0), w_sem, w_key))
              for lid in cand]
    scored.sort(key=lambda x: x[1], reverse=True)
    ranked_ids = [lid for lid, _ in scored if lid]

    elapsed = (time.perf_counter() - t0) * 1000

    # 4) Check if any gold session is in top-k
    gold_set = set(gold_ids)
    results_by_k: dict[int, bool] = {}
    for k in k_vals:
        top = ranked_ids[:k]
        results_by_k[k] = bool(set(top) & gold_set)

    # MRR: reciprocal rank of first gold hit
    rr = 0.0
    for rk, lid in enumerate(ranked_ids):
        if lid in gold_set:
            rr = 1.0 / (rk + 1)
            break

    if verbose:
        tag = f"R={rr:.2f}" if rr > 0 else "N/R"
        qtrunc = query[:55]
        print(f"  [{tag:>4}] {qtrunc:<55}  type={qtype:<15}  golds={len(gold_ids)}")

    return {
        "recall": results_by_k,
        "mrr": rr,
        "latency_ms": elapsed,
        "question_type": qtype,
    }


# ── LoCoMo data ────────────────────────────────────────────────────────────


def download_locomo() -> list[dict]:
    path = DATA_DIR / "locomo10.json"
    if path.exists():
        print(f"[data] LoCoMo loaded from {path}")
        return json.loads(path.read_text())
    print(f"[data] Downloading LoCoMo from {LOCOMO_URL}...")
    urllib.request.urlretrieve(LOCOMO_URL, path)
    data = json.loads(path.read_text())
    print(f"[data] Saved {len(data)} samples")
    return data


def extract_dialogues(conv: dict) -> list[dict]:
    """Replicates MemEval's locomo.extract_dialogues."""
    dialogues = []
    conv_data = conv.get("conversation", {})
    session_nums = []
    for key in conv_data:
        if key.startswith("session_") and not key.endswith("_date_time"):
            try:
                session_nums.append(int(key.split("_")[1]))
            except (ValueError, IndexError):
                pass
    for num in sorted(session_nums):
        session_key = f"session_{num}"
        dt_key = f"session_{num}_date_time"
        session_time = conv_data.get(dt_key, "")
        for turn in conv_data.get(session_key, []):
            if isinstance(turn, dict):
                dialogues.append({
                    "speaker": turn.get("speaker", "Unknown"),
                    "text": turn.get("text", ""),
                    "dia_id": turn.get("dia_id", ""),
                    "timestamp": session_time,
                })
    return dialogues


def answer_in_text(answer: Any, texts: list[str]) -> bool:
    """Check if answer text appears verbatim in any text (case-insensitive)."""
    if not isinstance(answer, str):
        answer = str(answer)
    answer_lower = answer.strip().lower()
    if not answer_lower or answer_lower in ("none", "unknown", "not found", "nan", "..."):
        return False
    for t in texts:
        if not isinstance(t, str):
            t = str(t)
        if answer_lower in t.lower():
            return True
    return False


def evaluate_locomo_sample(
    sample: dict, model: Any,
    corpus_tokens: list[list[str]], memory_ids: list[str], memory_texts: list[str],
    embeddings: np.ndarray, k_vals: list[int],
    w_sem: float, w_key: float, verbose: bool,
) -> dict:
    qa_pairs = sample.get("qa", [])
    results_by_k: dict[int, list[bool]] = {k: [] for k in k_vals}
    ranks: list[float] = []
    timing_ms: list[float] = []
    by_category: dict[int, dict] = {}

    for qa in qa_pairs:
        question = qa.get("question", "")
        answer = qa.get("answer", "")
        cat = qa.get("category", 0)

        t0 = time.perf_counter()

        # 1) Semantic: embed query, cosine similarity → top 200
        q_vec = model.encode(question, normalize_embeddings=True).astype(np.float32)
        cos_sims = embeddings @ q_vec
        sem_n = max(0, min(200, len(cos_sims) - 1))
        sem_idx = np.argpartition(-cos_sims, sem_n)[:sem_n]
        order = np.argsort(-cos_sims[sem_idx])
        sem_idx = sem_idx[order]
        sem_hits = {memory_ids[idx]: float(cos_sims[idx]) for idx in sem_idx}

        # 2) BM25 keyword (top-hit normalized)
        kw_hits = keyword_search_normalized(corpus_tokens, memory_ids, question)

        # 3) Hybrid ranking
        cand = set(sem_hits) | set(kw_hits)
        scored = [(lid, hybrid_score(sem_hits.get(lid, 0.0), kw_hits.get(lid, 0.0),
                                     w_sem, w_key))
                  for lid in cand]
        scored.sort(key=lambda x: x[1], reverse=True)
        ranked_ids = [lid for lid, _ in scored if lid]

        elapsed = (time.perf_counter() - t0) * 1000
        timing_ms.append(elapsed)

        # 4) Relevance check
        found = False
        for rk, lid in enumerate(ranked_ids):
            mi = memory_ids.index(lid)
            if answer_in_text(answer, [memory_texts[mi]]):
                ranks.append(1.0 / (rk + 1))
                found = True
                break
        if not found:
            ranks.append(0.0)

        for k in k_vals:
            top = ranked_ids[:k]
            hit = any(answer_in_text(answer, [memory_texts[memory_ids.index(lid)]])
                      for lid in top)
            results_by_k[k].append(hit)
            if cat not in by_category:
                by_category[cat] = {"hits": 0, "total": 0}
            by_category[cat]["total"] += 1
            if hit:
                by_category[cat]["hits"] += 1

        if verbose:
            tag = f"R={ranks[-1]:.2f}" if ranks[-1] > 0 else "N/R"
            a = str(answer)[:40] if not isinstance(answer, str) else answer[:40]
            print(f"  [{tag:>4}] q: {question[:55]:<55}  a: {a:<42}  cat={cat}")

    metrics: dict[str, Any] = {}
    for k in k_vals:
        hits = sum(results_by_k[k])
        metrics[f"recall@{k}"] = hits / len(results_by_k[k]) if results_by_k[k] else 0.0
    metrics["mrr"] = np.mean(ranks) if ranks else 0.0
    metrics["latency_ms"] = np.mean(timing_ms) if timing_ms else 0.0
    metrics["n_questions"] = len(qa_pairs)
    metrics["by_category"] = by_category
    return metrics


# ── Main ────────────────────────────────────────────────────────────────────


def run_locomo(model: Any, data: list[dict], samples: int | None,
               k_vals: list[int], w_sem: float, w_key: float,
               verbose: bool, label: str = "") -> dict:
    samples_to_run = data[:samples] if samples else data
    print(f"\n{'─'*60}")
    print(f"CONFIG: {label or f'sem={w_sem:.2f} kw={w_key:.2f}'}")
    print(f"{'─'*60}")

    all_metrics = []
    for i, sample in enumerate(samples_to_run):
        sid = sample.get("sample_id", f"sample_{i}")
        dialogues = extract_dialogues(sample)
        if not dialogues:
            continue
        n = len(dialogues)
        mids = [f"m{j}" for j in range(n)]
        mtexts = [d["text"] for d in dialogues]
        boost_tokens = [
            _tokenize(d.get("speaker", "")) * 3
            + _tokenize(d.get("timestamp", "")) * 2
            + _tokenize(d.get("text", ""))
            for d in dialogues
        ]
        embs = np.array(model.encode(mtexts, normalize_embeddings=True), dtype=np.float32)

        m = evaluate_locomo_sample(sample, model, boost_tokens, mids, mtexts, embs,
                                   k_vals, w_sem, w_key, verbose)
        all_metrics.append(m)
        if not verbose:
            parts = [f"R@{k}={m[f'recall@{k}']:.3f}" for k in k_vals]
            print(f"  [{sid}] turns={n:>4} qa={m['n_questions']:>3}  "
                  f"{' | '.join(parts)}  MRR={m['mrr']:.3f}")

    agg: dict[str, Any] = {}
    for k in k_vals:
        vals = [m[f"recall@{k}"] for m in all_metrics]
        agg[f"recall@{k}"] = {"mean": float(np.mean(vals)), "std": float(np.std(vals))}
    mrrs = [m["mrr"] for m in all_metrics]
    agg["mrr"] = {"mean": float(np.mean(mrrs)), "std": float(np.std(mrrs))}
    latencies = [m["latency_ms"] for m in all_metrics]
    agg["latency_ms"] = {"mean": float(np.mean(latencies)), "std": float(np.std(latencies))}
    agg["n_questions"] = sum(m["n_questions"] for m in all_metrics)
    agg["n_samples"] = len(all_metrics)

    # Per-category aggregate
    for k in k_vals:
        cat_sums: dict[int, dict[str, int]] = {}
        for m in all_metrics:
            for cat, d in m.get("by_category", {}).items():
                if cat not in cat_sums:
                    cat_sums[cat] = {"hits": 0, "total": 0}
                cat_sums[cat]["hits"] += d["hits"]
                cat_sums[cat]["total"] += d["total"]
        for cat, d in sorted(cat_sums.items()):
            r = d["hits"] / d["total"] if d["total"] else 0.0
            cname = CATEGORY_NAMES_LOCOMO.get(int(cat), str(cat))
            print(f"  R@{k} [{cname:<13}] = {r:.3f}  ({d['hits']}/{d['total']})")
        print()

    return agg


def run_longmemeval(model: Any, data: list[dict], samples: int | None,
                    k_vals: list[int], w_sem: float, w_key: float,
                    verbose: bool, label: str = "") -> dict:
    samples_to_run = data[:samples] if samples else data
    print(f"\n{'─'*60}")
    print(f"CONFIG: {label or f'sem={w_sem:.2f} kw={w_key:.2f}'}")
    print(f"Dataset: LongMemEval-S ({len(samples_to_run)} questions)")
    print(f"{'─'*60}")

    all_results: list[dict] = []
    for qi, question in enumerate(samples_to_run):
        if verbose:
            print(f"\n  [Q{qi}] {question.get('question', '')[:70]}")

        memory_ids, memory_texts, boost_tokens = ingest_longmemeval_question(question)
        if not memory_ids:
            continue

        embs = np.array(model.encode(memory_texts, normalize_embeddings=True),
                        dtype=np.float32)

        result = evaluate_longmemeval(
            question, model, memory_ids, boost_tokens, embs,
            k_vals, w_sem, w_key, verbose,
        )
        all_results.append(result)

        if not verbose:
            parts = [f"R@{k}={result['recall'].get(k, False)}" for k in k_vals]
            print(f"  [Q{qi}] {' | '.join(parts)}  MRR={result['mrr']:.3f}  "
                  f"type={result['question_type'][:20]}")

    agg: dict[str, Any] = {}
    for k in k_vals:
        vals = [r["recall"].get(k, False) for r in all_results if r["recall"].get(k) is not None]
        agg[f"recall@{k}"] = {
            "mean": float(np.mean(vals)) if vals else 0.0,
            "std": float(np.std(vals)) if vals else 0.0,
        }
    mrrs = [r["mrr"] for r in all_results]
    agg["mrr"] = {"mean": float(np.mean(mrrs)), "std": float(np.std(mrrs))}
    latencies = [r["latency_ms"] for r in all_results]
    agg["latency_ms"] = {"mean": float(np.mean(latencies)), "std": float(np.std(latencies))}
    agg["n_questions"] = len(all_results)

    # Per-category breakdown
    cat_results: dict[str, list[float]] = {}
    for r in all_results:
        qt = r.get("question_type", "unknown")
        if qt not in cat_results:
            cat_results[qt] = []
        cat_results[qt].append(r["mrr"])

    for k in k_vals:
        cat_recalls: dict[str, list[bool]] = {}
        for r in all_results:
            qt = r.get("question_type", "unknown")
            cat_recalls.setdefault(qt, []).append(r["recall"].get(k, False))

        print(f"\n  Per-category R@{k}:")
        for cat, vals in sorted(cat_recalls.items()):
            cname = CATEGORY_NAMES_LM.get(cat, cat)
            mean_r = float(np.mean(vals)) if vals else 0.0
            print(f"    [{cname:<18}] = {mean_r:.3f}  ({sum(vals)}/{len(vals)})")

    print("\n   Per-category MRR:")
    for cat, vals in sorted(cat_results.items()):
        cname = CATEGORY_NAMES_LM.get(cat, cat)
        mean_mrr = float(np.mean(vals)) if vals else 0.0
        print(f"    [{cname:<18}] = {mean_mrr:.3f}  ({len(vals)} questions)")

    return agg


def print_ablation(results: list[tuple[str, dict]], k_vals: list[int]):
    print("\n" + "=" * 80)
    print("ABLATION COMPARISON")
    print("=" * 80)
    header = f"{'Config':<30}" + "".join(f"{f'R@{k}':>10}" for k in k_vals) + f"{'MRR':>10}"
    print(header)
    print("-" * len(header))
    for label, agg in results:
        vals = "".join(f"{agg[f'recall@{k}']['mean']:>10.3f}" for k in k_vals)
        print(f"{label:<30}{vals}{agg['mrr']['mean']:>10.3f}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Lorekeeper hybrid retrieval algorithm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", choices=["longmemeval-s", "locomo"], default="longmemeval-s",
                        help="Dataset to evaluate (default: longmemeval-s)")
    parser.add_argument("--samples", type=int, default=None,
                        help="Number of samples (default: all)")
    parser.add_argument("--verbose", action="store_true", help="Print per-query results")
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5, 10],
                        help="Top-k values (default: 1 3 5 10)")
    parser.add_argument("--weights", type=float, nargs=2, metavar=("W_SEM", "W_KEY"),
                        default=[0.45, 0.30],
                        help="Hybrid weights (default: 0.45 0.30)")
    parser.add_argument("--semantic-only", action="store_true",
                        help="Shorthand for --weights 1.0 0.0")
    parser.add_argument("--keyword-only", action="store_true",
                        help="Shorthand for --weights 0.0 1.0")
    parser.add_argument("--ablate", action="store_true",
                        help="Run multiple weight combos and compare")
    args = parser.parse_args()

    if args.semantic_only:
        w_sem, w_key = 1.0, 0.0
    elif args.keyword_only:
        w_sem, w_key = 0.0, 1.0
    else:
        w_sem, w_key = args.weights

    from sentence_transformers import SentenceTransformer
    print("[model] Loading all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"[config] dataset={args.dataset}  k_vals={args.k}")

    if args.dataset == "locomo":
        data = download_locomo()
    else:
        data = download_longmemeval_s()
        print(f"[data] {len(data)} questions loaded")

    if args.ablate:
        combos = [
            (1.0, 0.0, "semantic-only"),
            (0.0, 1.0, "keyword-only"),
            (0.7, 0.3, "w_sem=0.70 w_kw=0.30"),
            (0.5, 0.5, "w_sem=0.50 w_kw=0.50"),
            (0.45, 0.30, "default (w_sem=0.45 w_kw=0.30)"),
            (0.3, 0.7, "w_sem=0.30 w_kw=0.70"),
        ]
        all_aggs = []
        for sw, kw, label in combos:
            if args.dataset == "locomo":
                agg = run_locomo(model, data, args.samples, args.k, sw, kw, False, label)
            else:
                agg = run_longmemeval(model, data, args.samples, args.k, sw, kw, False, label)
            all_aggs.append((label, agg))

        print_ablation(all_aggs, args.k)
    else:
        if args.dataset == "locomo":
            agg = run_locomo(model, data, args.samples, args.k, w_sem, w_key, args.verbose)
        else:
            agg = run_longmemeval(model, data, args.samples, args.k, w_sem, w_key, args.verbose)

        print("\n" + "=" * 60)
        print("AGGREGATE")
        print("=" * 60)
        for k in args.k:
            print(f"  recall@{k:<2}  = {agg[f'recall@{k}']['mean']:.3f} "
                  f"± {agg[f'recall@{k}']['std']:.3f}")
        print(f"  MRR        = {agg['mrr']['mean']:.3f} ± {agg['mrr']['std']:.3f}")
        print(f"  latency    = {agg['latency_ms']['mean']:.1f} "
              f"± {agg['latency_ms']['std']:.1f} ms/query")
        print(f"  questions  = {agg['n_questions']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
