---
id: LKPR-13
title: Implement lore_find_nearest_pairs for agent-driven memory consolidation
type: feature
status: backlog
priority: low
sprint: 3
rice_score: 11.7  # R:5 I:9 C:30% E:4w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-13] Implement lore_find_nearest_pairs for agent-driven memory consolidation

## Problem
Memories accumulate without any pruning or merging. Topics split across many fragmented entries. High-signal memories aren't distinguished from noise. No equivalent of the brain's sleep consolidation.

## Solution
Platform exposes a pure-math MCP tool: `lore_find_nearest_pairs(top_k, min_similarity)` — no LLM on platform side, pure vector dot-product over existing Chroma embeddings. Returns top-K memory pairs ranked by similarity with scores + content preview.

**Agent** makes all decisions: merge / keep / soft-delete. Merge = `lore_insert` (new combined memory) + `lore_update` (soft-delete originals).

Triggered by:
- Agent at session end if `lore_health` flags fragmentation > 30%
- Nightly cron (agent already warm — zero extra cost)

Platform never auto-merges. Every merge is reversible.

## Acceptance Criteria
- [ ] `lore_find_nearest_pairs(top_k, min_similarity)` returns memory pairs with similarity scores and content previews
- [ ] Pure vector math — no LLM calls on platform side
- [ ] Platform never auto-merges; agent makes all decisions
- [ ] Protocol skill (LKPR-3) updated with "if fragmentation > 30%, call `lore_find_nearest_pairs`" instruction
- [ ] Dashboard: consolidation review queue tab (optional but recommended)

## Affected Files
- New: `src/lorekeeper/services/consolidator.py`
- New: `loop/hooks/sleep_cycle.sh` or cron-driven Python script
- `src/lorekeeper/handlers.py` + `server.py` — register tool
- `src/lorekeeper/services/orchestrator.py` — expose cluster query
- Dashboard: new "Consolidation" tab for review queue

## Dependencies
- LKPR-2 (`lore_health` / `lore_stats`) — feeds cluster quality input; should be live first
- LKPR-9 (memory decay) — decayed memories are prime consolidation candidates

## Open Questions
- Clustering algorithm: k-means or HDBSCAN? (HDBSCAN preferred — no fixed k)
- Merge proposal format: show diff of what would be combined?
- Approval UX: dashboard tab or Telegram notification?

## Notes
High long-term value but low confidence (30%) — this is a genuinely hard problem. Build after Sprint 1 + 2 are solid. CLAUDE.md already references "sleep cycle" as a north star vision item.
