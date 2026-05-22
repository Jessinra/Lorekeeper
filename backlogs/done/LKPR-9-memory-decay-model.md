     1|---
     2|id: LKPR-9
     3|title: Add time-decay multiplier to hybrid scoring formula
     4|type: feature
     5|status: backlog
     6|priority: high
     7|sprint: 1
     8|rice_score: 44.8  # R:8 I:7 C:80% E:1w
     9|filed_by: Hermes
    10|filed_date: 2026-05-22
    11|---
    12|
    13|# [LKPR-9] Add time-decay multiplier to hybrid scoring formula
    14|
    15|## Problem
    16|Memories inserted months ago about dead projects stay just as prominent as fresh, relevant ones. Old context pollutes query results with no mechanism to naturally fade unless explicitly marked bad via feedback.
    17|
    18|## Solution
    19|Add a time-decay multiplier to the hybrid scoring formula:
    20|
    21|```
    22|decay = e^(-λ · days_since_last_used)
    23|final_score = combined_score × decay
    24|```
    25|
    26|- λ configurable via `LORE_DECAY_LAMBDA` env var
    27|- Memories with high `usage_count` resist decay (reinforcement)
    28|- Orphaned memories (no links, no usage) fade fastest
    29|
    30|## Acceptance Criteria
    31|- [ ] Decay multiplier is applied during re-ranking in `search.py`
    32|- [ ] `LORE_DECAY_LAMBDA` is documented in `config.py` with a sensible default (e.g. half-life ~90 days for unused memories)
    33|- [ ] `README.md` scoring formula section updated
    34|- [ ] Decay does not affect stored scores — applied only at query time
    35|- [ ] Optional: `decay_factor` exposed in search result output
    36|
    37|## Affected Files
    38|- `src/lorekeeper/services/search.py` — apply decay multiplier during re-ranking
    39|- `src/lorekeeper/config.py` — add `LORE_DECAY_LAMBDA` env var
    40|- `README.md` — update scoring formula docs
    41|
    42|## Dependencies
    43|_None_
    44|
    45|## Open Questions
    46|- What's a sensible default λ? (target: half-life of ~90 days for unused memories)
    47|- Should `decay_factor` be visible in search results?
    48|
    49|## Notes
    50|Decay logic does not exist yet — this is net-new. Prevents "memory swamp" as the store grows to hundreds of entries. Especially important for long-running projects.
    51|

## Completed
Date: 2026-05-22
Branch: feature/LKPR-9-time-decay-scoring
Commit: time_decay(), decay_factor in MCP response, decay_lambda in config + dashboard UI
Reviewed by: Akane — solid work ✓
