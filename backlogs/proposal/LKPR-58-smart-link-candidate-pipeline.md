---
id: LKPR-58
title: Smart link candidate pipeline — lore_recommend_links MCP tool + agent skill
type: feature
status: S:done
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 127
filed_date: 2026-06-03
---

# [LKPR-58] Smart link candidate pipeline — lore_recommend_links MCP tool + agent skill

## Problem

Memory links are rarely created because agents would have to manually read all memories and pair them up. The result: most memories are orphans with zero links, making `lore_related` and graph traversal features nearly useless.

Automated bulk-linking is not the goal — bad links are worse than no links. The goal is: **surface high-confidence candidates, let the agent decide.**

## Solution

A single-stage pipeline exposed via `lore_recommend_links`. Agent calls the tool, reviews the scored candidates (each has a per-signal score breakdown), and confirms links it trusts via `lore_insert`.

No LLM classifier inside the MCP server — the *agent* is the LLM. Lorekeeper just surfaces the data.

**Scorers (all env-configurable, no LLM):**

- **Cosine similarity** — batch ANN query over existing embeddings in Chroma/LanceDB
- **BM25 keyword overlap** — existing BM25 index in `services/keyword_index.py`
- **Entity/NER overlap** — spaCy `en_core_web_sm` (12MB); Jaccard overlap of named entities + noun phrases. Degrades gracefully if spaCy not installed.
- **Temporal decay** — `exp(-Δt / τ)`, τ=30d default. Soft bonus (weight 0.10).

Combined score (all weights env-configurable via `LORE_LINK_WEIGHT_*`):
```
score = 0.50·cosine + 0.30·bm25 + 0.10·entity + 0.10·temporal
```

Candidates below `LORE_LINK_SCORE_THRESHOLD` (default: 0.30) are dropped. Top-M returned (default: 10 via `LORE_LINK_TOP_M`).

**MCP tool: `lore_recommend_links(lore_id, top_k=None)`**

Returns candidates with per-signal scores. No `run_classifier`, no `proposed_relation` — the agent supplies the relation type when confirming via `lore_insert`.

**Agent skill: `lorekeeper-link-memories`**

Distributed via `assets/skills/`. Defines when to run, how to evaluate candidates, what makes a good link, and what to skip.

## Acceptance Criteria

- [x] `LinkCandidateGenerator` in `services/link_candidate.py` with pluggable scorer interface
- [x] `CosineScorer` — batch ANN query over existing embeddings
- [x] `BM25Scorer` — queries existing BM25 index, normalizes score
- [x] `EntityOverlapScorer` — spaCy NER Jaccard overlap, graceful degradation
- [x] `TemporalProximityScorer` — `exp(-Δt/τ)`, τ configurable via `LORE_LINK_TEMPORAL_TAU_DAYS`
- [x] Combined scorer: merges, thresholds, returns ranked list
- [x] Score threshold: `LORE_LINK_SCORE_THRESHOLD` env var (default: 0.3)
- [x] All scorer weights configurable: `LORE_LINK_WEIGHT_{COSINE,BM25,ENTITY,TEMPORAL}`
- [x] Skips pairs where a link already exists in either direction
- [x] `lore_recommend_links(lore_id, top_k=None)` registered in `server.py`
- [x] `top_k` overrides `LORE_LINK_TOP_M` for that call
- [x] Response: candidates with `weighted_score` and per-signal `scores` breakdown
- [x] Tool call tracked in `MetricsStore`
- [x] `assets/skills/lorekeeper-link-memories/SKILL.md` created and distributed via `setup.sh`
- [x] Skill covers: trigger conditions, review workflow, what makes a good link, pitfalls
- [x] Unit tests for each scorer with mock data
- [x] Integration test: pipeline returns expected candidates, none auto-written

## Decision Record

**LLM relation classifier REMOVED (2026-06-05).** Originally the PR included `LORE_LINK_CLASSIFIER_BASE_URL`, `LORE_LINK_CLASSIFIER_MODEL`, `run_classifier=True`, and `relation_classifier.py`. The agent already has an LLM — adding an inline httpx call inside the MCP server adds latency (30s per call), a new failure mode (HTTP timeout, API key management), and couples Lorekeeper to an inference provider it doesn't need. Stripped during PR review. `relation_classifier.py` deleted from the codebase.

## Affected Files

**Backend:**
- `src/lorekeeper/services/link_candidate.py` — new
- `src/lorekeeper/config.py` — add `LORE_LINK_*` env vars
- `src/lorekeeper/server.py` — register MCP tool

**Skills:**
- `assets/skills/lorekeeper-link-memories/SKILL.md` — new

## Dependencies

- LKPR-28: `lore_insert` inline links param — done ✓

## Required Updates

- **CLAUDE.md**: [x] Add `lore_recommend_links` to MCP API surface; add `LORE_LINK_*` env vars to table
- **README.md**: [x] Document `lore_recommend_links` tool
- **Skills**: [x] Covered in this ticket
- **Backlog**: [x] Close LKPR-59 (absorbed into this ticket)

## Notes

**Design principle:** Quality over quantity. No auto-write, no bulk backfill script. The agent is the decision-maker — the pipeline surfaces candidates, the agent confirms. A wrong link is worse than no link.

**No LLM in Lorekeeper:** The LLM classifier was removed after review. The agent calling the tool already has an LLM — Lorekeeper is a memory server, not an inference server.

**Research basis (June 2026):** Obsidian Smart Connections (500k users) uses cosine-only. No PKM tool uses NER, temporal, or co-retrieval signals. Entity overlap has highest precision for named-entity-dense notes. Temporal signal validated by PAM (arXiv:2602.11322) but must be a weak bonus.

**Future signals (not in scope):** Co-retrieval frequency tracking (LKPR-60+), spreading activation once graph density ≥ 2 avg links/node, bi-encoder fine-tuning after ~200 confirmed links.

**Absorbed:** LKPR-59 (lorekeeper-link-memories skill) merged into this ticket.