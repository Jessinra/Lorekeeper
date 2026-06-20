---
id: LKPR-98
title: Link type revision + orchestrated batch suggestion with review workflow
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 229
filed_date: 2026-06-20
supersedes: LKPR-67
---

# [LKPR-98] Link type revision + orchestrated batch suggestion with review workflow

## Problem

Two connected problems:

1. **Link types are ambiguous.** The current 8 types (`related_to`, `used_in`, `used_for`, `used_by`, `used_as`, ...) overlap semantically. `related_to` is a catch-all used everywhere because nothing else fits — makes the type field meaningless. Agents pick different `used_*` variants for the same relationship.

2. **Orphan memories never get connected.** `lore_recommend_links` exists but is pull-only — it only runs when someone explicitly queries a specific memory. Memories that no agent or human ever thinks to inspect remain isolated. A background sweep is the only thing that guarantees every memory gets a shot at being linked.

## Solution

Two phases, both non-LLM (math/ML scorers only).

### Phase 1 — Clean link types (absorbing LKPR-67)

Replace the current 8 types with 7 clear, distinct types:

| Type           | Meaning                     | Example                                         |
| -------------- | --------------------------- | ----------------------------------------------- |
| `references`   | Mentions or cites           | "Prompt caching" references "Claude API docs"   |
| `depends_on`   | Requires or builds upon     | "Auth middleware" depends_on "JWT token format" |
| `supersedes`   | Newer memory replaces older | "v2 API spec" supersedes "v1 API spec"          |
| `contradicts`  | Content conflicts           | "Benchmark A shows X" contradicts "B shows X"   |
| `part_of`      | Composition/hierarchy       | "Login page" part_of "Auth module"              |
| `derived_from` | Based on or inferred from   | "Retention pattern" derived_from "Cohort data"  |
| `causes`       | Direct causal relationship  | "Rate limit change" causes "Error 429 reports"  |

**Migration:** Read-side mapping for old links (no blocking write migration). Old types map via hardcoded dict. Background script provided for users who want to write-clean.

### Phase 2 — Orchestrated batch suggestion

A background cron job that sweeps all memories and suggests unlinked pairs:

#### Sweep algorithm

- Iterate all active (non-deleted) memories
- For each memory, run the existing `LinkCandidateGenerator` (cosine pre-filter → BM25 + entity overlap + temporal proximity → weighted combo)
- Candidates are collected into a `link_suggestions` DB table with no LLM involvement
- Pairs that already have a real link (either direction) are excluded
- Pairs that were previously rejected are excluded (soft-deleted in suggestions table)

#### Auto-accept threshold

- `LORE_SUGGEST_AUTO_ACCEPT_SCORE` (configurable, default ~0.85): candidates above this are auto-accepted — a real `memory_links` row is created with the top-scoring relation type, and the suggestion is removed
- Below threshold: saved as `pending`

#### Dedup

- Unique constraint on `(source_memory_id, target_memory_id)` in `link_suggestions` — both directions hash to the same canonical pair
- Repeated sweep runs upsert rather than duplicate

#### Scheduling

- Internal cron mechanism, configurable from the dashboard
- Default: every 12 hours
- Config env var: `LORE_SUGGEST_INTERVAL_HOURS`

#### Review workflow

- **MCP tools:**
  - `lore_get_suggestions(limit, min_score)` — fetch pending candidates
  - `lore_review_suggestion(id, action='accept'|'reject')` — accept creates real link (with suggested relation type), reject marks as soft-deleted in suggestions table
- **Dashboard:** new tab or sub-panel showing pending suggestions with accept/reject buttons + batch accept
- **Auto-expiry:** suggestions older than `LORE_SUGGEST_TTL_DAYS` (default 30) that were never acted on are pruned

#### On accept

1. Create a `memory_links` row using the candidate's top-weighted relation type (from the new Phase 1 set)
2. Remove the suggestion from `link_suggestions`

#### On reject

1. Set `status = 'rejected'` (soft deleted in suggestions table)
2. Never re-suggest this pair

## Acceptance Criteria

- [ ] **Phase 1:** `RelationType` literal updated to 7 new types; old types mapped on read via migration map; `lore_insert` rejects old types
- [ ] **Phase 2:** `link_suggestions` table created via DB migration (version N)
- [ ] **Phase 2:** Sweep script iterates all memories, runs `LinkCandidateGenerator`, writes candidates to link_suggestions
- [ ] **Phase 2:** Auto-accept above configurable threshold (creates real link, removes suggestion)
- [ ] **Phase 2:** Unique pair constraint (canonical ordering of source/target)
- [ ] **Phase 2:** Previously rejected pairs excluded from future sweeps
- [ ] **Phase 2:** MCP tools: `lore_get_suggestions`, `lore_review_suggestion`
- [ ] **Phase 2:** Dashboard tab with pending suggestions list, accept/reject/batch buttons
- [ ] **Phase 2:** Dashboard config section for sweep interval + auto-accept threshold
- [ ] **Phase 2:** Cron scheduling (Hermes cron or Python scheduler), default every 12h
- [ ] **Phase 2:** Auto-expiry for stale suggestions (>30 days unactioned)
- [ ] All existing tests pass; new tests for suggestion pipeline, MCP tools, dashboard view
- [ ] No LLM calls anywhere in the pipeline

## Affected Files

**Backend:**

- `src/lorekeeper/models.py` — `RelationType` literal, migration map, `LinkSuggestion` model
- `src/lorekeeper/services/database.py` — new migration for `link_suggestions` table
- `src/lorekeeper/services/link_store.py` — new `insert_suggestion`, `get_pending_suggestions`, `review_suggestion`, `reject_suggestion`, `prune_expired` methods
- `src/lorekeeper/services/link_candidate.py` — add batch `sweep_all()` method
- `src/lorekeeper/services/orchestrator.py` — `get_suggestions()`, `review_suggestion()`, `run_sweep()` methods
- `src/lorekeeper/config.py` — new env vars: `LORE_SUGGEST_AUTO_ACCEPT_SCORE`, `LORE_SUGGEST_INTERVAL_HOURS`, `LORE_SUGGEST_TTL_DAYS`
- `src/lorekeeper/server.py` — `lore_get_suggestions`, `lore_review_suggestion` MCP tools
- `scripts/migrate-link-types.py` (new) — optional write-migration for link types
- `scripts/sweep-links.py` (new) — entrypoint for cron job

**Dashboard:**

- `src/lorekeeper/dashboard/static/index.html` — new "Suggestions" tab
- `src/lorekeeper/dashboard/static/js/suggestions.js` (new) — suggestion list, accept/reject UI
- `src/lorekeeper/dashboard/static/css/styles.css` — suggestion styling
- `src/lorekeeper/dashboard/routes/suggestions.py` (new) — API routes for suggestions
- `src/lorekeeper/dashboard/app.py` — register new routes

## Dependencies

- LKPR-58 (smart link candidate pipeline) — already done, provides the scoring engine
- LKPR-67 (link type revision) — superseded by this ticket

## Required Updates

- **CLAUDE.md**: [ ] Document new link types, suggestion table, sweep scheduling
- **README.md**: [ ] Document new MCP tools and config options
- **Skills**: [ ] `lorekeeper-search` — update link type descriptions; `memory-linker` — update type set; `lorekeeper-reconcile` — note suggestion workflow

## Open Questions

- Sweep O(n) or O(n×K)? Current `LinkCandidateGenerator` already caps at `link_top_k` candidates per memory (cosine pre-filter is O(n) once per memory), so full sweep is O(n). Should be fast enough for 10K+ memories.
- Auto-accept threshold: default 0.85 seems high — may need tuning against real data. Make env-configurable so users can adjust.
- Should the sweep script be a standalone script or a Hermes cron job? Both viable — standalone is simpler and doesn't depend on the agent framework. Default to standalone script with cron.

## Notes

Combined from LKPR-67 (link types) and a new proposal for orchestrated batch link suggestion. The key insight is that `lore_recommend_links` is pull-only — orphans never get evaluated. A background sweep is the only way to guarantee coverage.
