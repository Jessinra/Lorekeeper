---
id: LKPR-99
title: Link suggestion sweep engine — periodic batch candidate generation with auto-accept
type: feature
sprint: 4
rice_score: ~
filed_by: Akane
github_issue: 231
filed_date: 2026-06-20
---

# [LKPR-99] Link suggestion sweep engine — periodic batch candidate generation with auto-accept

## Problem

`lore_recommend_links` is pull-only — it only runs when someone explicitly queries a specific memory. Memories that no agent or human ever inspects remain orphaned forever. No automatic process ensures every memory gets evaluated for connections.

## Solution

A sweep engine that periodically iterates all memories, runs the existing `LinkCandidateGenerator` scorers, and records candidates to a `link_suggestions` DB table — with auto-accept for high-confidence pairs.

The sweep uses the new link types defined in LKPR-67 (`references`, `depends_on`, `supersedes`, `contradicts`, `part_of`, `derived_from`, `causes`). LKPR-67 must land first or in parallel.

### 1. `link_suggestions` table

New DB table:

```sql
CREATE TABLE IF NOT EXISTS link_suggestions (
  id                TEXT PRIMARY KEY,
  source_memory_id  TEXT NOT NULL,
  target_memory_id  TEXT NOT NULL,
  source_title      TEXT NOT NULL,
  target_title      TEXT NOT NULL,
  weighted_score    REAL NOT NULL,
  cosine_score      REAL NOT NULL DEFAULT 0,
  bm25_score        REAL NOT NULL DEFAULT 0,
  entity_score      REAL NOT NULL DEFAULT 0,
  temporal_score    REAL NOT NULL DEFAULT 0,
  suggested_type    TEXT,                       -- best matching relation type (from LKPR-67 set)
  status            TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','accepted','rejected')),
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
  FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_suggestions_pair
  ON link_suggestions(source_memory_id, target_memory_id);
```

- **Uniqueness:** canonical pair ordering — always store `min(id1,id2)` as source, `max(id1,id2)` as target to prevent both-direction duplicates
- **Rejected** pairs stay with `status='rejected'` — future sweeps skip them
- **Accepted** pairs are removed after the real link is created

### 2. Sweep algorithm

```
for each active memory (non-deleted):
    candidates = LinkCandidateGenerator.generate(memory_id)
    for each candidate with weighted_score >= threshold:
        if pair already has real link → skip
        if pair previously rejected (status='rejected') → skip
        if candidate already exists as pending → upsert score
        if candidate.score >= auto_accept_score → create real link → remove suggestion
        else → insert as pending
```

- Uses the existing `LinkCandidateGenerator` from `link_candidate.py` — already O(n×K) thanks to cosine pre-filter (avoids O(n²) brute force)
- No LLM calls anywhere

### 3. Auto-accept

- **Threshold:** `LORE_SUGGEST_AUTO_ACCEPT_SCORE` (env config, default 0.85)
- On auto-accept: create a real `memory_links` row with a relation type, delete suggestion
- **Type selection heuristics:**
  - if temporal_score > 0.7 AND cosine_score > 0.8 → `derived_from`
  - if entity_score > 0.5 AND both spatial/temporal proximity → `part_of`
  - else → `references` (safe default)
  - All types are from the LKPR-67 set; the heuristic can be refined later

### 4. Scheduling

- Internal cron mechanism (standalone Python script, callable from cron/systemd)
- Env config: `LORE_SUGGEST_INTERVAL_HOURS` (default 12)
- Entrypoint: `scripts/sweep-links.py`
- **Auto-expiry:** prune suggestions older than `LORE_SUGGEST_TTL_DAYS` (default 30) that were never acted on

## Data flow summary

```
Sweep trigger (cron/button)
         ↓
LinkCandidateGenerator.generate(memory_id)  ← existing scorers
         ↓
   ┌─ score ≥ auto_accept ─→ insert memory_links → delete suggestion
   │
   └─ score < auto_accept ─→ insert pending suggestion
         ↓
   Agent reviews via MCP (LKPR-100) or dashboard (LKPR-101)
```

## Acceptance Criteria

- [ ] `link_suggestions` table created via DB migration (version N) with unique pair constraint
- [ ] `LinkSuggestionStore` in `services/link_store.py` — full CRUD for suggestions table
- [ ] Sweep function iterates all active memories, runs `LinkCandidateGenerator`, writes to link_suggestions
- [ ] Auto-accept: candidates above `LORE_SUGGEST_AUTO_ACCEPT_SCORE` create real `memory_links` rows automatically
- [ ] Type selection heuristics suggest appropriate relation type from LKPR-67 set
- [ ] Previously rejected pairs are excluded from future sweeps (read status='rejected')
- [ ] Already-linked pairs excluded (real link exists either direction)
- [ ] Unique pair constraint enforced (canonical ordering, no duplicates)
- [ ] Executable entrypoint: `scripts/sweep-links.py` for cron/systemd
- [ ] Config env vars: `LORE_SUGGEST_AUTO_ACCEPT_SCORE`, `LORE_SUGGEST_INTERVAL_HOURS`, `LORE_SUGGEST_TTL_DAYS`
- [ ] Auto-expiry: suggestions older than TTL are pruned
- [ ] No LLM calls anywhere in the pipeline
- [ ] All existing tests pass; new tests for suggestion pipeline (table operations, sweep algorithm, auto-accept logic)

## Dependencies

- LKPR-58 (smart link candidate pipeline) — provides the scoring engine (**done**)
- LKPR-67 (link type revision) — provides the relation types for auto-accept; should land first or simultaneously

## Required Updates

- **CLAUDE.md**: [ ] Document suggestion table, sweep scheduling, config vars
- **README.md**: [ ] Document new config options

## Notes

Split from LKPR-98 (combined meta-ticket). This is the backend engine only — MCP tools and dashboard UI are separate tickets (LKPR-100, LKPR-101). Link type revision is its own standalone ticket (LKPR-67) — this sweep engine consumes those types but does not define them.
