# LKPR-30: lore_reflect auto-creates memories from factual_discoveries and lessons_learnt

**Date:** 2026-06-02  
**Ticket:** LKPR-30 (S:ready → S:done)  
**Branch:** feat/lkpr-30-reflect-auto-insert

---

## Goal

When `lore_reflect` is called with `factual_discoveries` or `lessons_learnt`, auto-insert each item as a standalone searchable memory. Default opt-in (`auto_insert=True`). Each entry in `memories_created` includes a `relation` label (`discovered_in` / `learned_in`) and a `status` field (`inserted` or `duplicate`). No link records are created — the relation label is informational only.

---

## Files to Read Before Touching Anything

- [x] `src/lorekeeper/services/orchestrator.py` — `submit_reflection`, `_insert_one_memory`, `remember`
- [x] `src/lorekeeper/server.py` — `lore_reflect` signature
- [x] `tests/test_orchestrator.py` — existing reflect tests

---

## Affected Files

1. **`src/lorekeeper/services/orchestrator.py`** — `submit_reflection` gets `auto_insert` param; auto-insert loop after reflection is stored
2. **`src/lorekeeper/server.py`** — add `auto_insert: bool = True` param to `lore_reflect`, pass through; update docstring
3. **`tests/test_orchestrator.py`** — new tests for auto-insert behavior
4. **`README.md`** — document `auto_insert` on `lore_reflect`

> **Note:** `models.py` / `RelationType` was not modified. The `relation` field in `memories_created` is a plain string label in the return dict — no actual link records are created and no `RelationType` enum changes were needed.

---

## Implementation Steps

### Step 1: models.py — add new relation types

```python
RelationType = Literal["related_to", "used_in", "used_for", "used_by", "used_as",
                        "discovered_in", "learned_in"]
```

### Step 2: orchestrator.py — auto-insert loop in submit_reflection

Add `auto_insert: bool = True` param to `submit_reflection`.

After the reflection is stored (both `insert_reflection` and `upsert_session` calls), run:

```python
memories_created = []
if auto_insert:
    items = [
        (factual_discoveries, "discovered_in", 7.0),
        (lessons_learnt, "learned_in", 8.0),
    ]
    for items_list, relation, score in items:
        for text in items_list:
            title = self._extract_title(text)
            result = self._insert_one_memory(
                {"title": title, "description": title, "content": text, "score": score},
                force=False,
            )
            if "duplicate" in result:
                # Dedup blocked — still try to link back to reflection if memory exists
                mem_id = result["duplicate"]["existing_memory"]["id"]
            else:
                mem_id = result["inserted"]["id"]
            # Link memory → reflection (source=memory, target=reflection_id)
            # _insert_one_link validates relation_type, so discovered_in/learned_in must be in RELATION_TYPES first
            try:
                self._insert_one_link({
                    "source_memory_id": mem_id,
                    "target_memory_id": reflection_id,
                    "relation_type": relation,
                    "reason": f"auto-created from lore_reflect session {session_id}",
                })
            except Exception:
                log.warning("reflect_auto_link_failed", mem_id=mem_id, exc_info=True)
            memories_created.append({
                "id": mem_id,
                "title": title,
                "relation": relation,
            })
    if memories_created:
        self._rebuild_kw()
```

Return value becomes:
```python
return {
    "reflection_id": reflection_id,
    "session_id": session_id,
    "created_at": now,
    "memories_created": memories_created,
}
```

**Edge cases:**
- Empty lists → no inserts, `memories_created: []`
- Duplicates → still linked back to reflection (link might already exist — `_insert_one_link` raises if link is a dup; catch and swallow)
- `auto_insert=False` → skip loop entirely, return `memories_created: []`

### Step 3: server.py — wire the param

```python
async def lore_reflect(
    ...
    auto_insert: bool = True,
) -> dict:
```

Pass `auto_insert=auto_insert` to `submit_reflection`. Update docstring.

### Step 4: Tests (TDD order — write tests first)

```
test_reflect_auto_insert_creates_memories_from_discoveries
test_reflect_auto_insert_creates_memories_from_lessons
test_reflect_auto_insert_scores_correctly  (discoveries=7.0, lessons=8.0)
test_reflect_auto_insert_links_back_to_reflection
test_reflect_auto_insert_false_skips_creation
test_reflect_auto_insert_empty_lists_returns_empty
test_reflect_auto_insert_dedup_blocked_still_returns_existing_id
test_reflect_auto_insert_memories_created_in_return
```

### Step 5: README update

Add `auto_insert` to the `lore_reflect` parameter docs.

---

## Key Constraints

- `_insert_one_link` validates relation_type against `RELATION_TYPES` — must add to models.py FIRST
- Duplicate link insertion: `_insert_one_link` calls `links.insert_link` — check if that raises on duplicate or silently upserts
- `reflection_id` is a UUID, not a memory lore_id — the link target is a reflection, not a memory. `_insert_one_link` does `get_memory_row(target_memory_id)` validation — this will FAIL because reflection_id is not in the memories table. Need to use `links.insert_link` directly, bypassing `_insert_one_link`'s memory-existence validation.

---

## Pitfall: reflection_id is not a memory_id

`_insert_one_link` calls `_validate_relation_type` then `links.insert_link` directly (no target-memory existence check). Looking at the code again:

```python
def _insert_one_link(self, lnk: dict) -> dict:
    self._validate_relation_type(lnk.get("relation_type", ""))
    link = self.links.insert_link(
        source_memory_id=lnk["source_memory_id"],
        target_memory_id=lnk["target_memory_id"],
        ...
    )
```

No memory-existence check here — that check is only in `insert()` for inline links. So `_insert_one_link` can accept reflection_id as target. ✓

---

## Pitfall: link_store duplicate handling

Check `links.insert_link` — does it raise or upsert on duplicate? Need to handle gracefully.
