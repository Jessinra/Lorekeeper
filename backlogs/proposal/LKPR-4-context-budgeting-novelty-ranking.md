---
id: LKPR-4
title: Context budgeting and novelty ranking in lore_search
type: feature
status: proposal
priority: medium
sprint: 2
rice_score: 31.5  # R:7 I:6 C:75% E:1.5w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-4] Context budgeting and novelty ranking in lore_search

## Problem
Two related gaps in search quality:
1. The same high-scored memories dominate every search in a session — no freshness boost for things the agent hasn't seen yet
2. No way for an agent to say "give me results that fit in 500 tokens" — agent has to truncate manually

## Solution
**Novelty ranking:** Track which memory IDs were returned in the last N searches within a session. Apply a small score penalty (`LORE_NOVELTY_PENALTY`, default 0.1) for recently-surfaced memories to surface underexplored parts of the graph.

**Context budgeting:** New optional param on `lore_search`: `max_tokens: int`. Lorekeeper auto-truncates content fields to fit the budget and returns actual token count used alongside results.

## Acceptance Criteria
- [ ] `lore_search` accepts optional `max_tokens` param; results are truncated to fit and `tokens_used` is returned
- [ ] Recently-returned memories receive a configurable score penalty within the same session
- [ ] `LORE_NOVELTY_PENALTY` env var is documented in `config.py` and README
- [ ] Novelty state does not persist across server restarts (in-memory only is fine for v1)

## Affected Files
- `src/lorekeeper/services/search.py` — novelty tracking + budget trimming
- `src/lorekeeper/models.py` — session-scoped state for novelty
- `src/lorekeeper/config.py` — `LORE_NOVELTY_PENALTY` env var

## Dependencies
_None_

## Open Questions
- Session scoping: novelty state lives in-memory per server instance, or persisted in SQLite?
- Token counting: use tiktoken or simple word estimate?

## Notes
Two features bundled as they touch the same search pipeline. Both are purely additive — no schema changes.
