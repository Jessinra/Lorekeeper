---
id: LKPR-58
title: Smart link candidate pipeline — lore_recommend_links MCP tool + agent skill
type: feature
status: S:proposal
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-03
---

# [LKPR-58] Smart link candidate pipeline — lore_recommend_links MCP tool + agent skill

## Problem

Memory links are rarely created because agents would have to manually read all memories and pair them up. The result: most memories are orphans with zero links, making `lore_related` and graph traversal features nearly useless.

Automated bulk-linking is not the goal — bad links are worse than no links. The goal is: **surface high-confidence candidates, let the agent decide.**

## Solution

A two-stage pipeline exposed via a single MCP tool. Agent calls `lore_recommend_links`, reviews the scored candidates, and confirms links it trusts via `lore_insert`.

**Stage 1 — Candidate generation (no LLM)**

Four pluggable scorers, all reusing existing infra:

- **Cosine similarity** — batch ANN query over existing embeddings in Chroma/LanceDB
- **BM25 keyword overlap** — existing BM25 index in `services/keyword_index.py`
- **Entity/NER overlap** — spaCy `en_core_web_sm` (12MB); Jaccard overlap of named entities + noun phrases. Highest precision for fact-dense memories (same person, project, concept).
- **Temporal decay** — `exp(-Δt / τ)`, τ=4h default. Memories created close in time likely share context. Soft bonus only (weight 0.10) — validated by PAM paper (arXiv:2602.11322).

Combined score (all weights env-configurable via `LORE_LINK_W_*`):
```
score = 0.35·cosine + 0.35·bm25_norm + 0.20·entity_jaccard + 0.10·temporal_decay
```

Candidates below `LORE_LINK_CANDIDATE_THRESHOLD` (default: 0.45, overridable per-call via `min_score`) are dropped before Stage 2.

**Stage 2 — Relation classifier (LLM)**

For each Stage 1 candidate above threshold:
- Input: title + first sentence of each memory (~50 tokens/pair), batched
- Output: `related_to | contradicts | supersedes | depends_on | none`
- `none` is the noise filter — Stage 1 false positives get discarded here
- Model configurable via `LORE_LINK_CLASSIFIER_MODEL` env var

**MCP tool: `lore_recommend_links(n=10, min_score=None, run_classifier=True)`**

Returns top-N candidates with relation type, confidence, and per-signal breakdown. Agent reviews → calls `lore_insert(links=[...])` to create only the ones it trusts. No auto-write.

**Agent skill: `lorekeeper-link-memories`**

Distributed via `assets/skills/`. Defines when to run, how to evaluate candidates, what makes a good link, and what to skip.

## Acceptance Criteria

- [ ] `LinkCandidateGenerator` in `services/link_candidate.py` with pluggable scorer interface
- [ ] `CosineSimilarityScorer` — batch ANN query over existing embeddings
- [ ] `BM25OverlapScorer` — queries existing BM25 index, normalizes score
- [ ] `EntityOverlapScorer` — spaCy NER + noun phrases, Jaccard overlap
- [ ] `TemporalDecayScorer` — `exp(-Δt/τ)`, τ configurable via `LORE_LINK_TEMPORAL_TAU_HOURS` (default: 4)
- [ ] Combined scorer: merges, deduplicates, thresholds, returns ranked list
- [ ] Candidate threshold: `LORE_LINK_CANDIDATE_THRESHOLD` env var (default: 0.45)
- [ ] All scorer weights configurable: `LORE_LINK_W_{COSINE,BM25,ENTITY,TEMPORAL}`
- [ ] Skips pairs where a link already exists in either direction
- [ ] `RelationClassifier` base class with swappable backend
- [ ] `LLMRelationClassifier` — batched title+first-sentence prompt, parses enum output
- [ ] `none` relation type discards candidate from output
- [ ] `LORE_LINK_CLASSIFIER_MODEL` env var (default: agent's configured model)
- [ ] `lore_recommend_links(n=10, min_score=None, run_classifier=True)` registered in `handlers.py` and `server.py`
- [ ] `min_score` overrides `LORE_LINK_CANDIDATE_THRESHOLD` for that call
- [ ] `run_classifier=False` returns raw Stage 1 candidates with scores only (fast path)
- [ ] Response: `{memory_a: {id, title}, memory_b: {id, title}, relation_type, confidence, scorer_breakdown}`
- [ ] `scorer_breakdown` shows per-signal scores for agent transparency
- [ ] Tool call tracked in `MetricsStore`
- [ ] `assets/skills/lorekeeper-link-memories/SKILL.md` created and distributed via `setup.sh`
- [ ] Skill covers: trigger conditions, review workflow, what makes a good link, pitfalls
- [ ] Unit tests for each scorer with mock data
- [ ] Unit test for LLM classifier with mocked response
- [ ] Integration test: pipeline on small fixture DB returns expected candidates, none auto-written

## Affected Files

**Backend:**
- `src/lorekeeper/services/link_candidate.py` — new
- `src/lorekeeper/services/relation_classifier.py` — new
- `src/lorekeeper/config.py` — add `LORE_LINK_*` env vars
- `src/lorekeeper/handlers.py` — add `lore_recommend_links` handler
- `src/lorekeeper/server.py` — register MCP tool
- `src/lorekeeper/schemas.py` — add `RecommendLinksInput/Output`

**Skills:**
- `assets/skills/lorekeeper-link-memories/SKILL.md` — new

**Dashboard:**
- _none_

## Dependencies

- LKPR-28: `lore_insert` inline links param — done ✓
- LKPR-20: `lore_related` graph traversal — parallel, not blocking

## Required Updates

- **CLAUDE.md**: [ ] Add `lore_recommend_links` to MCP API surface; add `LORE_LINK_*` env vars to table
- **README.md**: [ ] Document `lore_recommend_links` tool
- **Skills**: [ ] Covered in this ticket
- **Backlog**: [ ] Close LKPR-59 (absorbed into this ticket)

## Open Questions

- spaCy model size: `en_core_web_sm` (12MB) vs `en_core_web_md` (43MB). Recommend sm default, configurable via `LORE_LINK_SPACY_MODEL`.

## Notes

**Design principle:** Quality over quantity. No auto-write, no bulk backfill script. The agent is the decision-maker — the pipeline surfaces candidates, the agent confirms. A wrong link is worse than no link.

**Research basis (June 2026):** Obsidian Smart Connections (500k users) uses cosine-only. No PKM tool uses NER, temporal, or co-retrieval signals. Entity overlap has highest precision for named-entity-dense notes. Temporal signal validated by PAM (arXiv:2602.11322) but must be a weak bonus — spurious links from temporally-close but unrelated memories are a real risk.

**Future signals (not in scope):** Co-retrieval frequency tracking (LKPR-60+), spreading activation once graph density ≥ 2 avg links/node, bi-encoder fine-tuning after ~200 confirmed links.

**Absorbed:** LKPR-59 (lorekeeper-link-memories skill) merged into this ticket.
