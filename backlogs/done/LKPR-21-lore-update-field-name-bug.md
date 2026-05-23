---
id: LKPR-21
title: lore_update memory_feedback expects "id" not "memory_id" — API inconsistency
type: bug
status: closed
reason: not reproducible
priority: high
rice_score: ~
filed_by: Hermes (Akane)
filed_date: 2026-05-23
---

# [LKPR-21] lore_update memory_feedback expects "id" not "memory_id"

## Symptom
Calling `lore_update(memory_feedback=[{memory_id: "uuid", useful: true, confidence: 8}])` fails with `'id'` error — the field name must be `id`, not `memory_id`.

Reproduction:
```python
# Fails:
lore_update(memory_feedback=[{memory_id: "52ec8d3b-...", useful: true, confidence: 8}])
# → {errors: [{id: "?", error: "'id'"}]}

# Works:
lore_update(memory_feedback=[{id: "52ec8d3b-...", useful: true, confidence: 8}])
# → {updated_memories: 1}
```

## Notes
- Every other Lorekeeper tool uses `memory_id` or `session_id` as the identifier field name (e.g. `lore_insert` uses `memory_id` in output, `lore_reflect` uses `session_id`, `lore_update` output uses `id` for the updated memory count but the *input* feedback object expects bare `id`)
- `link_feedback` in the same `lore_update` tool may have the same issue — `source_id`/`target_id` vs just `id`
- This broke the feedback loop during reflection — agent can't train trust scores

## Acceptance Criteria
- [ ] `lore_update` `memory_feedback` objects accept `id` (not `memory_id`) — this is the canonical field, fix doc if it says otherwise
- [ ] `link_feedback` objects checked for same issue — should use `id` not `link_id`
- [ ] MCP tool description updated in `handlers.py` to show `id` as the field name in the schema JSON
- [ ] No backward compat scope — callers fix their field name, period

## Effort
XS — fix the schema description in handlers.py

## How to Test

### Unit test (handler level)
```python
# 1. Happy path — "id" is the canonical field
result = await lore_update_handler({
    "memory_feedback": [{"id": mem_id, "useful": True, "confidence": 8}]
})
assert len(result["errors"]) == 0

# 2. "memory_id" should fail — only "id" is accepted
result = await lore_update_handler({
    "memory_feedback": [{"memory_id": mem_id, "useful": True, "confidence": 8}]
})
assert "'id'" in str(result["errors"])  # clear error

# 3. link_feedback — only "id" accepted
result = await lore_update_handler({
    "link_feedback": [{"id": link_id, "score": 0.8}]
})
assert len(result["errors"]) == 0

# 4. link_feedback with "link_id" should fail
result = await lore_update_handler({
    "link_feedback": [{"link_id": link_id, "score": 0.8}]
})
assert "'id'" in str(result["errors"])

# 5. Invalid UUID — still returns error
result = await lore_update_handler({
    "memory_feedback": [{"id": "bad-uuid", "useful": True, "confidence": 8}]
})
assert len(result["errors"]) > 0

# 6. Empty feedback
result = await lore_update_handler({"memory_feedback": []})
assert len(result["errors"]) == 0
```

### Integration test (smoke test)
```bash
# 1. Search for an existing memory → get its id
# 2. Call lore_update with {id: ...} — must succeed
# 3. Call lore_update with {memory_id: ...} — must fail with "'id'" error
```

### How to spot callers using the wrong field
Once the fix is in, grep all agent configs / cron prompts / skills for `memory_id` or `link_id` near `lore_update`:
```bash
grep -rn "memory_id\|link_id" ~/.hermes/backlogs/ ~/Code/lorekeeper/backlogs/
```
Update any hits to use `id`.

## How to Prevent Similar Cases

### Root cause
The MCP handler in `src/lorekeeper/handlers.py` defines the tool schema JSON with a field name that may not match what the handler code actually reads. There is no enforcement that the advertised schema field names match the handler's actual expectations.

### Prevention measures

1. **Schema introspection test** — Add a test that calls `tools/list` on the server, parses each tool's `inputSchema.properties`, and verifies every field name appears in the corresponding handler code (or a Pydantic model). If the schema says `id` but the handler looks for `memory_id`, the test catches it.

2. **Pydantic boundary model** — The handler should deserialize into a Pydantic model at the entry point. The field name in the model **is** the source of truth. If you rename the field in Pydantic, both the schema description and the handler logic update atomically.

3. **Add to code review checklist in CLAUDE.md** — "MCP tool input schema field names must match handler code." One line, catches the human error before PR merge.