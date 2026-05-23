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

After every `lore_insert`, do a lightweight vector ANN scan against the existing store using the new memory's embedding (already computed by the insert path). If the top match has `semantic_score > threshold`, auto-create a `MemoryLink` with `relation_type: "related_to"` and reason `"auto-linked (cosine: 0.91)"`.

- No LLM call — pure vector math, sub-100ms
- Threshold configurable via `LORE_AUTO_LINK_THRESHOLD` env var (default 0.85)
- Max 1 link per insert to avoid noise (or configurable max)
- Insert itself is not blocked — linking is additive
- The link reason includes the similarity score so agents can inspect quality

Note: this detects **closeness** (semantic similarity), not **relational intent** (agent-defined connections). Two different use cases — this one handles clusters/duplicates. LKPR-28 handles agent-intended links.

## Acceptance Criteria

- [ ] After lore_insert, the inserted memory is auto-linked to its closest existing match if similarity > threshold
- [ ] Link stored as `MemoryLink` with `relation_type: "related_to"` and reason including cosine score
- [ ] Threshold configurable via `LORE_AUTO_LINK_THRESHOLD` env var
- [ ] Insert completes successfully even if no match found (not enforced)
- [ ] No duplicate links for the same pair (guard against repeated inserts hitting the same match)
- [ ] Config documented in README

## Affected Files

**Backend:**
- `src/lorekeeper/services/orchestrator.py` — call link_store after insert
- `src/lorekeeper/config.py` — add `LORE_AUTO_LINK_THRESHOLD`
- `tests/test_lore_related.py` or `tests/test_orchestrator.py` — assert auto-link created

**Dashboard:**
_none_

## Dependencies

_None_ — embedding is already computed by the insert pipeline. Pure addition.

## Open Questions

- BFS in embedding space vs just top-1? Top-1 is simpler and less noisy.
- Should auto-linked memories also get reciprocal links from the pre-existing node back? (symmetry)
- Should this run inline (on every insert) or as an idle batch pass? Inline is simpler; batch is better if insert volume is high.

## Notes

Pairs with LKPR-28 (inline links param). They solve different problems:
- **LKPR-27** = machine-detected clusters (passive, automatic, for dedup/navigation)
- **LKPR-28** = agent-intended relations (active, explicit, for knowledge graph)