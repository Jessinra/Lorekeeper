---
id: LKPR-9
title: Add time-decay multiplier to hybrid scoring formula
type: feature
status: done
priority: high
sprint: 1
rice_score: 44.8  # R:8 I:7 C:80% E:1w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-9] Add time-decay multiplier to hybrid scoring formula

## Problem
Memories inserted months ago about dead projects stay just as prominent as fresh, relevant ones. Old context pollutes query results with no mechanism to naturally fade unless explicitly marked bad via feedback.

## Solution
Add a time-decay multiplier to the hybrid scoring formula:

```
decay = e^(-λ · days_since_last_used)
final_score = combined_score × decay
```

- λ configurable via `LORE_DECAY_LAMBDA` env var
- Memories with high `usage_count` resist decay (reinforcement)
- Orphaned memories (no links, no usage) fade fastest

## Acceptance Criteria
- [x] Decay multiplier is applied during re-ranking in `search.py`
- [x] `LORE_DECAY_LAMBDA` is documented in `config.py` with a sensible default (e.g. half-life ~90 days for unused memories)
- [x] `README.md` scoring formula section updated
- [x] Decay does not affect stored scores — applied only at query time
- [x] Optional: `decay_factor` exposed in search result output

## Affected Files
- `src/lorekeeper/services/search.py` — apply decay multiplier during re-ranking
- `src/lorekeeper/config.py` — add `LORE_DECAY_LAMBDA` env var
- `README.md` — update scoring formula docs

## Dependencies
_None_

## Open Questions
- What's a sensible default λ? (target: half-life of ~90 days for unused memories)
- Should `decay_factor` be visible in search results?

## Notes
Decay logic does not exist yet — this is net-new. Prevents "memory swamp" as the store grows to hundreds of entries. Especially important for long-running projects.

## Completed
Date: 2026-05-22
Branch: feature/LKPR-9-time-decay-scoring
Commit: time_decay(), decay_factor in MCP response, decay_lambda in config + dashboard UI
Reviewed by: Akane — solid work ✓