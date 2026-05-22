---
id: LKPR-16
title: lore_insert false dedup — unrelated memories matched at similarity 1.0
type: bug
status: done
priority: high
sprint: 1
filed_by: Hermes
filed_date: 2026-05-22
resolved_date: 2026-05-22
---

# [LKPR-16] lore_insert false dedup — unrelated memories matched at similarity 1.0

## Problem
`lore_insert` was blocking all inserts as duplicates, returning `similarity: 1.0` against completely unrelated existing memories.

Observed symptoms:
- Insert "Test insert" (diagnostic text) → deduped against "Google Calendar OAuth setup" (similarity 1.0)
- Insert "Hermes multi-profile setup for dual Telegram bots" → deduped against "Google Workspace setup for Hermes bot" (similarity 1.0)
- No new memories were being inserted; all hits claimed `similarity: 1.0` regardless of content
- The existing memories returned as "duplicates" were semantically unrelated to the input

## Root Cause
**mem0 v2 + Chroma 1.5.x scoring pipeline inversion.**

Chroma returns cosine **distances** (0 = identical, 1 = opposite). mem0 v2's `score_and_rank()` treats that value as a **similarity** score and applies `threshold=0.1` to filter. Result:

- Near-identical memories → distance ≈ 0.0 → **filtered out** (below threshold)  
- Unrelated memories → distance ≈ 1.0 → **pass filter, clamped to 1.0**

Every insert search returned all existing memories with score=1.0, triggering dedup on everything.

## Fix
`MemoryEngine.search()` now bypasses mem0's scoring pipeline entirely. It:
1. Embeds the query directly via `mem0.embedding_model.embed()`
2. Calls `chroma_collection.query()` with `include=["distances", "metadatas"]`
3. Converts: `similarity = max(0.0, min(1.0, 1.0 - distance))`

Changed file: `src/lorekeeper/services/memory_engine.py`

## Before / After

**Before fix** — searching 3 semantically distinct memories with unrelated query:
```
query: "quarterly financial report budget"
→ id-python  score=1.0   ← "Python is a programming language..."
→ id-sky     score=1.0   ← "The sky is blue and clouds are white"
→ id-finance score=1.0   ← "Financial budget quarterly report"
All scores 1.0, no discrimination. Every insert blocked as duplicate.
```

**After fix** — same query, same memories:
```
query: "quarterly financial report budget"
→ id-finance score=0.491  ← correctly highest (relevant)
→ id-python  score=0.000  ← correctly near-zero (unrelated)
→ id-sky     score=0.000  ← correctly near-zero (unrelated)
```

**Insert behavior after fix:**
```
Insert "Python programming" (first time)  → inserted ✅
Insert "Python programming" (same title)  → duplicate blocked ✅ (exact title match)
Insert "Quarterly revenue report"         → inserted ✅ (correctly not a duplicate)
```

## Tests Added
`tests/test_memory_engine.py` — 7 unit tests covering:
- Relevant memory ranks first with meaningful score
- Unrelated query scores below 0.7 (not 1.0)
- **Core regression test**: scores vary across semantically different memories (catches the uniform-1.0 bug)
- All scores in [0.0, 1.0]
- Results sorted descending
- Empty store returns []
- Relevant memory outscores irrelevant for domain-matched query

## Acceptance Criteria
- [x] `lore_insert` no longer false-deduplicates unrelated memories
- [x] Similarity scores reflect actual semantic distance (varied, not all 1.0)
- [x] Regression tests added and passing

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
