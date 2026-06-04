---
id: LKPR-30
github_issue: 17
title: lore_reflect auto-creates memories from factual_discoveries and lessons_learnt
type: feature
sprint: 1
rice_score: ~ # TBD: R:9 I:9 C:80% E:0.5w
filed_by: Akane (PM)
filed_date: 2026-05-24
---

# [LKPR-30] lore_reflect auto-creates memories from discoveres and lessons

## Problem

`lore_reflect` already receives `factual_discoveries: list[str]` and `lessons_learnt: list[str]` — these are **pre-formed atomic memories**. But the tool just stores them in a reflection record and does nothing else. The agent does the hard work of extracting insights during reflection, then those insights evaporate because nothing turns them into memories.

**Real data:** My PM study reflection had 18 `factual_discoveries` items and 6 `lessons_learnt`. Zero became lorekeeper memories. That's 24 lost nodes.

## Solution

When `lore_reflect` is called with `factual_discoveries` or `lessons_learnt`, auto-insert each item as a lorekeeper memory and link it back to the reflection.

**New param**: `auto_insert: bool = true` on `lore_reflect`.

**Behavior when auto_insert=true:**

1. For each item in `factual_discoveries`:
   - `lore_remember(item)` — same auto-extract logic as LKPR-29
   - Plus link: `{from: memory_id, to: reflection_id, relation: "discovered_in"}`
   - Score: 7
2. For each item in `lessons_learnt`:
   - `lore_remember(item)` — auto-extract
   - Plus link: `{from: memory_id, to: reflection_id, relation: "learned_in"}`
   - Score: 8 (lessons are higher value)

**Return value gets extended:**

```
{
  "reflection_id": "r-123",
  "session_id": "s-456",
  "memories_created": [
    {"id": "m-1", "title": "85% of product failures...", "relation": "discovered_in"},
    {"id": "m-2", "title": "Premortem technique...", "relation": "learned_in"}
  ]
}
```

**If LKPR-27 (auto-link) is live**, the individual memories also get auto-linked to their nearest neighbors during insert. Double win.

## Acceptance Criteria

- [ ] `lore_reflect` with `auto_insert=true` creates one memory per `factual_discoveries` and `lessons_learnt` item
- [ ] Each memory is linked back to the reflection via `discovered_in` or `learned_in` relation
- [ ] `auto_insert=true` is the default (opt-out, not opt-in)
- [ ] If no discoveries/lessons, no memories created (silent)
- [ ] Return object includes `memories_created` array
- [ ] Duplicate guard: if a discovery was already inserted in a prior reflection, dedup blocks it
- [ ] Updates `lore_reflect` MCP tool description to document the new behavior

## Affected Files

**Backend:**

- `src/lorekeeper/schemas.py` — add `auto_insert: bool` to reflect schema
- `src/lorekeeper/services/orchestrator.py` — auto-insert loop
- `src/lorekeeper/handlers.py` — extend return value
- `tests/test_orchestrator.py` — assert memories created from discoveries, links created

**Dashboard:**
_none_ — reflection view already shows discoveries/lessons; memories link back to it

## Dependencies

LKPR-29 (`lore_remember`) — this reuses the same auto-extract logic. Can ship independently by calling `memory_engine.insert()` directly with auto-extracted fields, but cleaner if LKPR-29's handler is reusable.

## Required Updates

- **CLAUDE.md**: [ ] Update agentic loop section — the reflection→memory bridge is now automated
- **README.md**: [ ] Document the `auto_insert` behavior on `lore_reflect`
- **Skills**: [ ] Update `reflect` skill — reflection output format changed (includes `memories_created` in response)
- **Backlog**: [ ] N/A

## Open Questions

- Should discoveries from DIFFERENT reflections on the same session be deduped? Yes — use existing dedup threshold.
- What about `decisions` field? Lower priority — decisions are more narrative and less atomic than discoveries. Skip for v1.

## Notes

This is the **single highest-ROI automation** in the friction chain. The agent already generates structured insights during reflection. Zero marginal effort to turn them into memories — the work is already done. This just adds the final write step.

Estimated effort: 0.5 week. Mostly wiring + tests.
