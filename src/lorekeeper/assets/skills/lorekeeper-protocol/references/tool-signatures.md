# Tool Signatures

Reference for `lorekeeper-protocol`. Tool signatures and parameter schemas.

## `lore_search`

```json
{
  "query": "string",
  "min_score": 0.1,
  "include_links": true,
  "include_deleted": false,
  "limit": null
}
```

## `lore_insert`

Two patterns: **A. Inline links** (preferred — include `links` inside the memory dict) and **B. Top-level links** (require explicit `source_memory_id`).

**Pitfall:** `__NEW__` is NOT a valid placeholder. Use inline links or a two-step insert.

**Valid `relation_type`:** `causes`, `contradicts`, `depends_on`, `derived_from`, `part_of`, `references`, `supersedes`. Use `references` as default. `related_to`, `supports`, `used_in` are rejected.

## `lore_remember`

```json
{ "thought": "Single thought to store verbatim." }
```

Fast one-shot insert — auto-extracts title, auto-links to nearest semantic neighbor (≥0.75).

## `lore_update`

```json
{
  "memory_feedback": [{ "id": "...", "useful": true }],
  "link_feedback": [{ "id": "...", "useful": true }]
}
```

## `lore_reflect`

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

**Pitfall:** Duplicate `session_id` returns `already_processed: true` and skips auto_insert.

## `lore_processed_sessions`

```json
{}
```

Returns array of reflected session IDs.

## `lore_forget`

```json
{
  "memory_ids": ["<id1>", "<id2>"],
  "reason": "duplicate | hallucinated | outdated | expired | unspecified"
}
```

## `lore_recommend_links`

```json
{ "lore_id": "<uuid>", "top_k": 10 }
```

Returns scored link candidates. Never writes — call `lore_insert` with `links=[]` to confirm.
