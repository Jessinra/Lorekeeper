---
name: lorekeeper-protocol
description: Full session protocol for using Lorekeeper MCP tools correctly. Load at the start of any session that uses Lorekeeper. Covers when and how to call lore_search, lore_remember, lore_insert, lore_update, lore_reflect, and lore_processed_sessions across all five phases — session start, mid-session topic shift, health maintenance, topic consolidation, and session end.
version: 1.1.0
---

# Lorekeeper Protocol

Follow this protocol every session to keep your memory store accurate, healthy, and growing.

---

## Phase 1 — Session Start

**Trigger**: Beginning of every session, before any substantive work.

### Steps

1. Identify the session topic (1–3 keywords).
2. Search for context:

```
lore_search({ query: "<topic>", min_score: 0.15, include_links: true })
```

3. Read all returned memories — decisions made, constraints, past patterns.
4. Provide feedback on every result immediately:

```
lore_update({
  memory_feedback: [
    { id: "<id>", useful: true },
    { id: "<id>", useful: false }
  ]
})
```

Mark `useful: true` if relevant to this session. `useful: false` for noise. Skip only if zero results.

5. If fewer than 3 results, run a broader fallback search with related terms.

**Do not skip Phase 1.** Working without context causes duplicate inserts and contradictory decisions.

---

## Phase 2 — Mid-Session (Topic Shift)

**Trigger**: Conversation shifts to a new domain, subsystem, or question.

1. Detect the shift.
2. Run a fresh `lore_search` for the new topic — same pattern as Phase 1.
3. Provide feedback on the new result set.

**Rule**: If you're reasoning about something you haven't searched for, search first.

---

## Phase 3 — Session End

**Trigger**: End of every session.

1. **Insert new memories** for anything discovered:
   - Decisions (with rationale), bugs fixed (root cause), architecture insights
   - User corrections — strongest learning signal
   - Patterns that generalize

   Use the `lorekeeper-memorize` skill for each insert.

2. **Reflect**:

```
lore_reflect({
  session_id: "<YYYY-MM-DD-topic-slug>",
  summary: "What was done, decided, and learned.",
  topic: "<topic>",
  task_type: "build | debug | review | design",
  what_was_done: "...",
  decisions: "...",
  lessons_learnt: ["..."],
  good_patterns: ["..."],
  factual_discoveries: ["..."],
  memory_ids: ["<ids of key memories inserted>"]
})
```

---

## Quick Reference

| Phase               | When                | Tools                         |
| ------------------- | ------------------- | ----------------------------- |
| **1 — Start**       | Every session start | `lore_search`, `lore_update`  |
| **2 — Mid-session** | On topic shift      | `lore_search`, `lore_update`  |
| **3 — End**         | Every session end   | `lore_insert`, `lore_reflect` |

---

## Rules

- **Search before insert** — prevents fragmentation from duplicates
- **Feedback after every search** — how quality signals propagate
- **One fact per memory** — dense memories degrade search precision
- **Standalone memories** — must make sense with zero conversation context
- **User corrections are gold** — insert immediately when pushed back on
- **Session end is not optional** — `lore_reflect` feeds the consolidation loop

---

## Tool Signatures

### `lore_search`

```json
{
  "query": "string",
  "min_score": 0.1,
  "include_links": true,
  "include_deleted": false,
  "limit": null
}
```

### `lore_remember`

```json
{
  "thought": "Single thought to store verbatim."
}
```

Fast one-shot insert — zero friction. Use for quick capture during a session. Auto-extracts title (first ~80 chars), stores content verbatim, default score 7.0. Auto-links to nearest neighbor ≥ 0.75. Returns `{id, title, linked_to}`.

Prefer `lore_remember` for individual insights. Use `lore_insert` when you need explicit titles, descriptions, scores, or manual links.

### `lore_insert`

```json
{
  "memories": [{ "title": "...", "description": "...", "content": "..." }],
  "links": [
    {
      "source_memory_id": "...",
      "target_memory_id": "...",
      "relation_type": "related_to",
      "reason": "..."
    }
  ],
  "force": false
}
```

### `lore_update`

```json
{
  "memory_feedback": [{ "id": "...", "useful": true }],
  "link_feedback": [{ "id": "...", "useful": true }]
}
```

### `lore_reflect`

```json
{
  "session_id": "YYYY-MM-DD-topic-slug",
  "summary": "...",
  "topic": "...",
  "task_type": "build | debug | review | design",
  "what_was_done": "...",
  "decisions": "...",
  "lessons_learnt": ["..."],
  "good_patterns": ["..."],
  "factual_discoveries": ["..."],
  "user_profile_updates": ["..."],
  "memory_ids": ["..."],
  "session_date": "YYYY-MM-DD"
}
```

### `lore_processed_sessions`

```json
{}
```

Returns array of session IDs already reflected.
