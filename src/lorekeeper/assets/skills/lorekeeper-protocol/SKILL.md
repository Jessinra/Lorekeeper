---
name: lorekeeper-protocol
description: Full session protocol for using Lorekeeper MCP tools correctly. Load at the start of any session that uses Lorekeeper. Covers when and how to call lore_search, lore_insert, lore_update, lore_reflect, and lore_processed_sessions across all five phases — session start, memory reconstruction, topic shift, session end, and health maintenance.
version: v2.0.0
---

# Lorekeeper Protocol

Follow this protocol every session to keep your memory store accurate, healthy, and growing.

Inspired by MRAgent (Ji et al., NUS, ICML 2026): **memory is reconstructed, not retrieved.** Instead of a static one-shot search, actively explore the memory graph — search, reason, follow links, prune dead ends, repeat. See `references/mragent.md` for the full research summary.

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

## Phase 1.5 — Active Memory Reconstruction (MRAgent-inspired)

**Trigger**: After Phase 1 completes, before acting on retrieved memories.

Instead of treating the initial search results as final, actively reconstruct the memory context by iteratively exploring the memory graph. The LLM's reasoning guides each subsequent search step.

### Reconstruction Loop

Run this loop until the information surface is exhausted:

```
1. READ top results from the current batch.
2. REASON about what's still unknown:
   - What cues can I infer from what I've read?
   - What temporal anchors, relationships, or constraints are hinted at?
   - What would disprove or confirm my current understanding?
3. TRAVERSE links from high-value memories:
   - Follow `references`, `depends_on`, `part_of` edges to discover related content
   - Use lore_search with specific IDs to fetch linked targets
4. SEARCH for inferred cues:
   - Formulate new queries based on what reasoning revealed
   - lore_search({ query: "<new-cue>", min_score: 0.1 })
5. PRUNE dead ends:
   - lore_update(useful=false) on memories that turned out irrelevant
   - This prevents re-exploring the same paths in subsequent iterations
6. REPEAT steps 1-5.
7. BREAK when 2 consecutive iterations return no novel relevant results.
```

### Example

```
Initial search: "Nate video game tournaments" → finds 3 memories about events
Reasoning: "These mention July as a key date. I should search for July-specific activities."
Follow-up search: "July tournament logistics"
Traverse links from tournament memory → find linked "participant contact" memory
→ richer context than any single query would produce
```

**Rule**: If you've read a memory and still have open questions about the topic, run another search before concluding — don't settle for the first batch.

---

## Phase 2 — Mid-Session (Topic Shift)

**Trigger**: Conversation shifts to a new domain, subsystem, or question.

### Steps

1. Detect the shift.
2. Run a fresh `lore_search` for the new topic — same pattern as Phase 1.
3. **Link graph traversal**: also follow links from any already-known relevant memories found in Phase 1 or 1.5. The new topic may connect to existing knowledge via shared tags.
4. Provide feedback on the new result set.
5. If the topic feels connected to something already explored, run the reconstruction loop (Phase 1.5) at reduced depth (1–2 iterations).

**Rule**: If you're reasoning about something you haven't searched for, search first.

---

## Phase 3 — Session End

**Trigger**: End of every session.

### Steps

1. **Insert new memories** for anything discovered:

   - Decisions (with rationale), bugs fixed (root cause), architecture insights
   - User corrections — strongest learning signal
   - Patterns that generalize
   - **Cue-tag associations**: when storing a new memory, think about what cues should trigger it. Insert explicit `references` links to related existing memories so future traversals can find it via graph paths, not just keyword search.

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

## Phase 4 — Health Maintenance (as needed)

**Trigger**: When you notice stale, contradictory, or orphaned memories.

1. Search for duplicate or overlapping memories.
2. Use `lore_insert` to consolidate (with `force: true` if needed).
3. Mark old versions with `lore_update(useful=false)` to let the score system deprioritize them.
4. Add `supersedes` links from old to new.

---

## Quick Reference

| Phase                    | When                | Tools                                        |
| ------------------------ | ------------------- | -------------------------------------------- |
| **1 — Start**            | Every session start | `lore_search`, `lore_update`                 |
| **1.5 — Reconstruction** | After Phase 1       | `lore_search`, `lore_update`, link traversal |
| **2 — Mid-session**      | On topic shift      | `lore_search`, `lore_update`, link traversal |
| **3 — End**              | Every session end   | `lore_insert`, `lore_reflect`                |
| **4 — Health**           | As needed           | `lore_insert`, `lore_update`, `lore_forget`  |

---

## Rules

- **Search before insert** — prevents fragmentation from duplicates
- **Feedback after every search** — how quality signals propagate
- **Reconstruct, don't just retrieve** — one-shot search is a starting point, not an answer
- **Prune dead ends actively** — `lore_update(useful=false)` trains the relevance system and prevents re-exploring empty paths
- **Follow links** — the memory graph's edge structure is more informative than flat search; traverse it
- **One fact per memory** — dense memories degrade search precision
- **Standalone memories** — must make sense with zero conversation context
- **Store with cues in mind** — when inserting, link to related memories so future traversals find them
- **User corrections are gold** — insert immediately when pushed back on
- **Session end is not optional** — `lore_reflect` feeds the consolidation loop

---

## Pitfalls

- **`__NEW__` is not a valid ID placeholder** — You can't reference a memory being created in the same call. Use inline links (inside the memory dict) to auto-link new memories to existing targets, or insert in two steps.
- **Duplicate session IDs block auto_insert** — `lore_reflect` with a previously-used `session_id` returns `already_processed: true` and skips inserting factual_discoveries and lessons_learnt. Always use unique session IDs.
- **Consolidated memories are landing pages** — When searching a well-explored topic, `source_type: consolidated` memories (from prior lore_reflect calls) often contain the richest summarizations. Read them first — they may eliminate the need for additional search iterations.
- **`lore_search` with `ids` bypasses scoring** — When fetching by ID list, the relevance engine is skipped. The `combined_score` will be 0.0 for all results. This is normal — it means exact-lookup mode, not evaluation mode.
- **Link types are strict** — Only `causes`, `contradicts`, `depends_on`, `derived_from`, `part_of`, `references`, `supersedes` are valid. Types like `related_to`, `supports`, `used_in`, `used_for`, `used_by`, `used_as` will be rejected with validation errors. Use `references` as the default.

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

### `lore_insert`

Two patterns for linking:

**A. Inline links (preferred)** — include `links` inside the memory dict. The source is automatically set to the memory being created:

```json
{
  "memories": [
    {
      "title": "...",
      "description": "...",
      "content": "...",
      "links": [
        {
          "target_memory_id": "<existing-id>",
          "relation_type": "references",
          "reason": "..."
        }
      ]
    }
  ],
  "force": false
}
```

**B. Top-level links** — require explicit `source_memory_id`:

```json
{
  "memories": [{ "title": "...", "description": "...", "content": "..." }],
  "links": [
    {
      "source_memory_id": "<existing-id>",
      "target_memory_id": "<existing-id>",
      "relation_type": "references",
      "reason": "..."
    }
  ],
  "force": false
}
```

**Pitfall**: `__NEW__` is NOT a valid placeholder for `source_memory_id` or `target_memory_id` in either pattern. You cannot reference a memory being created in the same call. To link a new memory to existing ones, use pattern A (inline links) or do a two-step insert: (1) insert the memory without links, (2) insert links with the returned ID.

**Valid `relation_type` values:** `causes`, `contradicts`, `depends_on`, `derived_from`, `part_of`, `references`, `supersedes`. Use `references` as the default. Types like `related_to`, `supports`, `used_in`, `used_for`, `used_by`, `used_as` are NOT valid and will be rejected with a validation error.

### `lore_remember`

```json
{
  "thought": "Single thought to store verbatim."
}
```

Fast one-shot insert — zero friction. Auto-extracts title (first ~80 chars at word boundary), stores content verbatim, default score from `new_memory_default_score` (5.0), auto-links to nearest semantic neighbor (similarity ≥ 0.75). Use for quick session capture. Both `lore_remember` and `lore_insert` are equally first-class tools.

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

**Pitfall**: If `session_id` has already been reflected (even by another agent or auto-consolidation), the call returns `already_processed: true` and does NOT insert new factual_discoveries or lessons_learnt as memories (auto_insert is skipped). Always use a unique session_id — typically `{YYYY-MM-DD}-{unique-topic-slug}`. If you get `already_processed`, check whether the existing reflection already covers your findings.

### `lore_processed_sessions`

```json
{}
```

Returns array of session IDs already reflected.

### `lore_forget`

```json
{
  "memory_ids": ["<id1>", "<id2>"],
  "reason": "duplicate | hallucinated | outdated | expired | unspecified"
}
```

Soft-deletes memories. Use for cleanup in Phase 4.
