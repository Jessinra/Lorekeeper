---
id: LKPR-27
title: Upgrade auto-link to configurable — env vars, lore_insert hook, dedup guard
type: feature
status: backlog
priority: medium
sprint: ~
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-05-23
updated: 2026-05-26
---

# [LKPR-27] Auto-link similar/duplicate memories on insert via vector similarity

## Problem

LKPR-29 shipped a basic `_auto_link()` in `remember()` — hardcoded top-2 candidates, 0.75 threshold, max 1 link. It works for the basic case but has no env-var control, no duplicate-link guard, and `lore_insert()` doesn't use it at all.

Without configurable knobs:
- Can't tighten/loosen the threshold per deployment
- Can't disable auto-link entirely (no kill switch)
- `lore_insert` users miss out on automatic graph building

## Solution

Refactor the existing `_auto_link()` into a configurable, reusable method and hook it into `insert()` as well.

**Current `_auto_link()` (already in code):**
```python
sem_hits = self._engine.search(thought, limit=2)
for hit in sem_hits:
    if hit["lore_id"] != lore_id and hit["score"] >= 0.75:
        link A→B, max 1 link
```

**Upgrade to:**
```python
# settings: LORE_AUTO_LINK_K, LORE_AUTO_LINK_THRESHOLD, LORE_AUTO_LINK_ENABLED
sem_hits = search(text, limit=settings.k)
for hit in sem_hits:
    if hit["lore_id"] != lore_id and hit["score"] >= settings.threshold:
        if not already_linked(self, lore_id, hit["lore_id"]):
            link A→B
```

Changes:
1. **Promote hardcoded values → config.py env vars** — `LORE_AUTO_LINK_K` (default 5), `LORE_AUTO_LINK_THRESHOLD` (default 0.85), `LORE_AUTO_LINK_ENABLED` (default true)
2. **Add duplicate link guard** — check `link_store` before inserting a link that already exists
3. **Extend to `lore_insert`** — call `_auto_link()` after `_insert_one_memory()` succeeds
4. `_auto_link` already handles `lore_remember` — nothing changes there, just picks up the new settings

## Acceptance Criteria

- [ ] `LORE_AUTO_LINK_ENABLED` env var (default true) — when false, `_auto_link()` is a no-op for both `remember()` and `insert()`
- [ ] `LORE_AUTO_LINK_K` env var (default 5) — how many candidates to fetch from vector search
- [ ] `LORE_AUTO_LINK_THRESHOLD` env var (default 0.85) — minimum cosine score to create a link
- [ ] `_auto_link()` uses the new env vars instead of hardcoded 2/0.75
- [ ] `lore_insert` calls `_auto_link()` after each successful memory insert
- [ ] Duplicate guard: same A→B pair is never linked twice (check `link_store` before inserting)
- [ ] `lore_remember` continues working as before, just picks up the new defaults (k=5, threshold=0.85)
- [ ] Config documented in README with threshold rationale
- [ ] **Dashboard:** Auto-link controls added to Config tab (enabled toggle, k spinbutton, threshold spinbutton) under their own "AUTO-LINK" section
- [ ] **Dashboard:** Auto-link metrics tracked and visible (links created count via `_increment_metric`)

## Affected Files

**Backend:**
- `src/lorekeeper/services/orchestrator.py` — call vector store after insert, create links
- `src/lorekeeper/config.py` — add `LORE_AUTO_LINK_K`, `LORE_AUTO_LINK_THRESHOLD`, `LORE_AUTO_LINK_ENABLED`
- `tests/test_orchestrator.py` — assert auto-link created with correct score, no-link for low-similarity inserts, no duplicate link on second insert

**Dashboard:**
- `src/lorekeeper/dashboard/app.py` — add `auto_link_enabled`, `auto_link_k`, `auto_link_threshold` to `get_config()` return + `ConfigUpdate` model
- `src/lorekeeper/dashboard/static/js/config.js` — add `auto_link` section to `CFG_FIELDS` with enabled toggle, k spinbutton, threshold spinbutton; render + save
- `src/lorekeeper/dashboard/static/index.html` — add `.config-section` container for auto-link
- `src/lorekeeper/dashboard/static/js/metrics.js` — add `auto_linked` to `TOOL_COLORS` for the metrics heatmap

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