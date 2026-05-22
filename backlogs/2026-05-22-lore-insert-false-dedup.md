---
id: LKPR-16
title: lore_insert false dedup — unrelated memories matched at similarity 1.0
type: bug
status: backlog
priority: high
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-16] lore_insert false dedup — unrelated memories matched at similarity 1.0

## Problem
`lore_insert` is blocking all inserts as duplicates, returning `similarity: 1.0` against completely unrelated existing memories.

Observed symptoms:
- Insert "Test insert" (diagnostic text) → deduped against "Google Calendar OAuth setup" (similarity 1.0)
- Insert "Hermes multi-profile setup for dual Telegram bots" → deduped against "Google Workspace setup for Hermes bot" (similarity 1.0)
- No new memories are being inserted; all hits claim `similarity: 1.0` regardless of content mismatch
- The existing memories returned as "duplicates" are semantically unrelated to the input

## Solution
Investigate the dedup/similarity pipeline in `memory_engine.py`. Likely candidates:
- Embedding comparison returning wrong value (e.g. wrong vector being compared, zero-vector edge case)
- Similarity threshold misconfigured (set too low, or score normalisation bug making everything 1.0)
- Dedup check comparing wrong fields (e.g. comparing against a constant or stale value)

## Acceptance Criteria
- [ ] Inserting a genuinely new memory stores it successfully
- [ ] Inserting an actual duplicate is correctly blocked (similarity near 1.0 for real matches)
- [ ] Similarity score for unrelated memories is well below dedup threshold

## Affected Files
- `src/lorekeeper/services/memory_engine.py` — similarity/dedup logic (unverified)
- `src/lorekeeper/handlers.py` — insert handler (unverified)

## Dependencies
_None_

## Open Questions
- Is this regression or was dedup never working correctly?
- Does it affect all memories or only recently inserted ones?
- Is the bug in embedding generation or in score comparison?

## Notes
Filed 2026-05-22 by Hermes during diagnostic testing of `lore_insert`.
Root cause is unverified — symptoms observed, investigation not yet done.
Reproduced in Telegram session; separate CLI session could search/read fine.
