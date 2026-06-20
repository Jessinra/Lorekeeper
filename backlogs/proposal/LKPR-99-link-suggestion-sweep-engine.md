---
id: LKPR-99
title: Link suggestion sweep engine — periodic batch candidate generation with auto-accept
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 231
filed_date: 2026-06-20
absorbed: LKPR-67 (link types)
---

# [LKPR-99] Link suggestion sweep engine — periodic batch candidate generation with auto-accept

## Problem

`lore_recommend_links` is pull-only — it only runs when someone explicitly queries a specific memory. Memories that no agent or human ever inspects remain orphaned forever. No automatic process ensures every memory gets evaluated for connections.

## Solution

A sweep engine that periodically iterates all memories, runs the existing `LinkCandidateGenerator` scorers, and records candidates to a `link_suggestions` DB table — with auto-accept for high-confidence pairs.

This ticket also **absorbs LKPR-67** (link type revision) since the sweep needs to suggest the new types.

### 1. New link types (from LKPR-67)

Replace the current 8 ambiguous types with 7 clear ones:

| Type           | Meaning                     | Example                                         |
| -------------- | --------------------------- | ----------------------------------------------- |
| `references`   | Mentions or cites           | "Prompt caching" references "Claude API docs"   |
| `depends_on`   | Requires or builds upon     | "Auth middleware" depends_on "JWT token format" |
| `supersedes`   | Newer memory replaces older | "v2 API spec" supersedes "v1 API spec"          |
| `contradicts`  | Content conflicts           | "Benchmark A shows X" contradicts "B shows X"   |
| `part_of`      | Composition/hierarchy       | "Login page" part_of "Auth module"              |
| `derived_from` | Based on or inferred from   | "Retention pattern" derived_from "Cohort data"  |
| `causes`       | Direct causal relationship  | "Rate limit change" causes "Error 429 reports"  |

**Migration:** Read-side mapping for old links (no blocking write migration). Old types map via hardcoded dict (e.g. `related_to` → `references`, `used_in` → `part_of`). Optional write-migration script for users who want to clean their DB.

### 2. `link_suggestions` table

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
  suggested_type    TEXT,                       -- best matching relation type
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

- Unique constraint on canonical pair (always store `min(id1,id2)` as source, `max(id1,id2)` as target to prevent both-direction duplicates)
- Rejected pairs are kept with `status='rejected'` — future sweeps skip them
- Accepted pairs are kept briefly (accepted → real link created → suggestion removed)

### 3. Sweep algorithm

```
for each active memory (non-deleted):
    candidates = LinkCandidateGenerator.generate(memory_id)
    for each candidate with weighted_score >= threshold:
        if pair already has real link → skip
        if pair previously rejected (status='rejected') → skip
        if candidate already exists as pending → upsert score
        if candidate.score >= auto_accept_score → create real link, remove suggestion
        else → insert as pending
```

- Uses the existing `LinkCandidateGenerator` from `link_candidate.py` — already O(n×K), cosine pre-filter avoids O(n²)
- No LLM calls anywhere

### 4. Auto-accept

- Configurable threshold: `LORE_SUGGEST_AUTO_ACCEPT_SCORE` (default 0.85)
- When auto-accepted: create a real `memory_links` row with the best-matching new relation type, delete the suggestion
- Relation type selection: the existing scores (cosine, BM25, entity, temporal) could suggest a type — for v1, default to `references` for most, with `depends_on` or `derived_from` when temporal+cosine both high

### 5. Scheduling

- Internal cron mechanism (Hermes cron or standalone Python scheduler)
- Configurable from env: `LORE_SUGGEST_INTERVAL_HOURS` (default 12)
- Standalone entrypoint: `scripts/sweep-links.py` — callable from cron or systemd timer
- Auto-expiry: prune suggestions older than `LORE_SUGGEST_TTL_DAYS` (default 30) that were never acted on

## Acceptance Criteria

- [ ] `models.py` `RelationType` literal updated to 7 new types
- [ ] Read-side migration map for old link types; `lore_insert` rejects old types
- [ ] `link_suggestions` table created via DB migration (version N) with unique pair constraint
- [ ] `LinkSuggestionStore` in `services/link_store.py` — CRUD for suggestions table
- [ ] Sweep function iterates all active memories, runs `LinkCandidateGenerator`, writes to link_suggestions
- [ ] Auto-accept: candidates above threshold create real links automatically
- [ ] Previously rejected pairs excluded from future sweeps
- [ ] Executable entrypoint: `scripts/sweep-links.py` for cron/systemd
- [ ] Config env vars: `LORE_SUGGEST_AUTO_ACCEPT_SCORE`, `LORE_SUGGEST_INTERVAL_HOURS`, `LORE_SUGGEST_TTL_DAYS`
- [ ] No LLM calls anywhere in the pipeline
- [ ] All existing tests pass; new tests for suggestion pipeline

## Dependencies

- LKPR-58 (smart link candidate pipeline) — already done, provides the scoring engine

## Required Updates

- **CLAUDE.md**: [ ] Document new link types, suggestion table, sweep scheduling
- **README.md**: [ ] Document new config options

## Notes

Split from LKPR-98 (combined meta-ticket). This is the backend engine only — MCP tools and dashboard UI are separate tickets (LKPR-100, LKPR-101). Absorbs LKPR-67 (link type revision).
