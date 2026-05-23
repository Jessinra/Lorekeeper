---
id: LKPR-27
title: Auto-link similar/duplicate memories on insert via vector similarity
type: feature
status: backlog
priority: medium
sprint: ~
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-23
---

# [LKPR-27] Auto-link similar/duplicate memories on insert via vector similarity

## Problem

New memories exist in isolation — no links to existing nodes. Over time this creates a dense cluster of semantically similar memories that aren't connected, making graph traversal (lore_related) less useful. Duplicate or near-duplicate entries accumulate without detection.

## Solution

After every `lore_insert`, query Chroma's existing HNSW index for the new memory's nearest neighbors. Auto-link to neighbors that pass both filters.

**Algorithm (ε-NN + top-k hybrid):**
```
top-k = query_chroma(embedding, n_results=5)       # HNSW fast-query, sub-100ms
candidates = [n for n in top-k if n.score > 0.85]  # threshold filter
for c in candidates:
    link_store.link(c.memory_id, new_memory_id, "auto_linked", f"cosine: {c.score:.2f}")
```

Key points:
- **Piggybacks on existing Chroma HNSW index** — no new index or storage needed. Chroma's internal graph is already a navigable small-world for the full store.
- **Threshold range**: 0.85 is safe for `all-MiniLM-L6-v2` embeddings (>0.95 = near-duplicate, >0.85 = strong same-topic cluster, >0.75 = related). Configurable via env var.
- **k=5 cap**: prevents hub flooding (one vague memory linking to everything). Controls graph density.
- **No LLM call** — pure vector math. At most 5 cosine comparisons (Chromai already scored them).
- **Insert is never blocked** — linking is additive only.
- **Reason includes cosine score** for agent inspection + tuning.

Contrast with LKPR-28: this detects **closeness** (semantic proximity), not **relational intent** (why A connects to B). Two different link types.

## Acceptance Criteria

- [ ] After lore_insert, query Chroma for top-k nearest neighbors (k configurable, default 5)
- [ ] For each neighbor with score > threshold (default 0.85), create `MemoryLink` with `relation_type: "auto_linked"` and reason `"cosine: {score:.2f}"`
- [ ] No links created if no neighbors pass threshold (silent skip)
- [ ] Guard against duplicate link creation (same A→B pair shouldn't re-link if A is inserted again)
- [ ] `LORE_AUTO_LINK_K` (env var, default 5) — how many candidates to fetch
- [ ] `LORE_AUTO_LINK_THRESHOLD` (env var, default 0.85) — minimum cosine score
- [ ] `LORE_AUTO_LINK_ENABLED` (env var, default true) — kill switch
- [ ] Config documented in README with threshold rationale

## Affected Files

**Backend:**
- `src/lorekeeper/services/orchestrator.py` — call vector store after insert, create links
- `src/lorekeeper/config.py` — add `LORE_AUTO_LINK_K`, `LORE_AUTO_LINK_THRESHOLD`, `LORE_AUTO_LINK_ENABLED`
- `tests/test_orchestrator.py` — assert auto-link created with correct score, no-link for low-similarity inserts, no duplicate link on second insert

**Dashboard:**
_none_ — existing link display shows auto_linked results naturally

## Dependencies

_None_ — Chroma's HNSW index is already built and maintained by every insert. The query path is already implemented. No new storage or services.

## Required Updates

- **CLAUDE.md**: [ ] N/A — passive feature, no workflow change
- **README.md**: [ ] Document `LORE_AUTO_LINK_ENABLED`, `LORE_AUTO_LINK_K`, `LORE_AUTO_LINK_THRESHOLD` env vars
- **Skills**: [ ] Update `memory-linker` skill — linking now has automatic and manual modes
- **Backlog**: [ ] N/A — complementary with LKPR-28

## Open Questions

- **Symmetry**: should auto-linked memories also get a reciprocal link back? (A→B and B→A). Creates bidirectional edges but doubles link count. Proposed: skip for now, revisit if graph traversal needs it.
- **Mutual filter**: only link if both A's embedding ranks B AND B's embedding would rank A (mutual k-NN). Produces higher-quality edges. Could be a toggle `LORE_AUTO_LINK_MUTUAL` for Phase 2.
- **Recency bias**: older memories might have drifted while new ones cluster. Worth an after-threshold that decays score by memory age? Probably over-engineering for v1.

## Notes

Research notes on embedding-based graph construction:

| Approach | What it does | Problem |
|----------|-------------|---------|
| **ε-NN** (threshold only) | Connect all pairs > 0.85 | Hub nodes with degree 100+ |
| **k-NN** (top-k only) | Each node gets exactly k edges | Weak matches at k=5 still link at 0.4 |
| **Mutual k-NN** | Only if A ranks B AND B ranks A | Sparsest, highest quality |

Our approach = **ε-NN + top-k hybrid** (cap by k, floor by threshold). Two knobs, no noise.

Typical cosine ranges for all-MiniLM-L6-v2 embeddings:
- >0.95: near-duplicate (merge candidate)
- 0.85–0.95: strong same-topic (safe auto-link)
- 0.75–0.85: related but distinct (possible, needs tuning)
- <0.75: too weak for auto-linking

Pairs with LKPR-28:
- **LKPR-27** = machine-detected (passive, automatic, for dedup/navigation)
- **LKPR-28** = agent-intended (active, explicit, for knowledge graph)