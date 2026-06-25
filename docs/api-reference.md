# Lorekeeper API Reference

Lorekeeper exposes **10 MCP tools** over stdio. All tools follow the [MCP protocol](https://modelcontextprotocol.io) — any MCP-compatible agent can use them.

## Tools

| Tool                      | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| `lore_search`             | Hybrid semantic + keyword search with relevance scores   |
| `lore_remember`           | Fast one-shot memory save (auto-titles, auto-links)      |
| `lore_insert`             | Bulk structured insert with custom scores and links      |
| `lore_update`             | Feedback loop — rate memories, drive quality             |
| `lore_forget`             | Soft-delete wrong or outdated memories                   |
| `lore_reflect`            | End-of-session: extract learnings, auto-save discoveries |
| `lore_processed_sessions` | Check which sessions are already processed               |
| `lore_recommend_links`    | Suggest candidate links between related memories         |
| `lore_get_suggestions`    | List pending link suggestions from the sweep engine      |
| `lore_review_suggestion`  | Accept or reject one or more link suggestions (batch)    |

---

## `lore_search`

```json
{
  "query": "checkout payment flow",
  "min_score": 0.1,
  "include_links": true,
  "include_deleted": false,
  "refine_from": null,
  "format": "full",
  "ids": null,
  "created_after": null,
  "updated_after": null,
  "sort_by": "relevance"
}
```

Returns ranked memories with relevance scores and linked memories.

### Two search modes

**Query mode** (default) — runs the hybrid semantic + BM25 pipeline:

- `query` (required unless `ids` is set): search text
- `min_score` (default `0.1`): minimum `combined_score` threshold — applied to the combined score _before_ time-decay
- `refine_from`: list of `lore_id` strings from a previous result to re-rank only within that candidate set. Unknown IDs silently ignored. Max 200 (configurable via `LORE_MAX_REFINE_FROM_IDS`)
- `format`: `"full"` (default) returns complete memory objects with relevance scores; `"title"` returns compact `{id, title, score}` for lower token cost
- `limit`: max results (defaults to `LORE_SEARCH_LIMIT`)
- `include_links` (default `true`): forced off in `format='title'` mode
- `include_deleted` (default `false`)
- `created_after` (optional): ISO 8601 UTC timestamp — only return memories with `created_at ≥ T`. Naive strings treated as UTC. Non-UTC offsets raise an error. Composes with all other filters.
- `updated_after` (optional): ISO 8601 UTC timestamp — only return memories with `updated_at ≥ T`. Same UTC rules as `created_after`.
- `sort_by` (default `"relevance"`): controls result ordering. `"relevance"` ranks by hybrid score when the search pipeline runs; in **ids lookup mode** (when `ids` is set) there is no scoring, so `"relevance"` preserves the caller-provided `ids` order instead. `"recent"` sorts by `updated_at DESC`. `"frequent"` sorts by `usage_count DESC`. Composes with timestamp filters and `limit`.

**ID lookup mode** — when `ids` is set, skips the vector/BM25 pipeline entirely and fetches those specific `lore_id`s directly from SQL. `query` is ignored. Unknown IDs silently ignored. Max 50 IDs (configurable via `LORE_MAX_SEARCH_IDS`). Pair with `format='title'` for a two-step list-then-fetch workflow. `created_after`, `updated_after`, and `sort_by` all compose with the ids path.

### Hybrid scoring formula

```
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
final    = combined × decay
```

Where:

- `semantic` — cosine similarity from the vector store (LanceDB), normalised to [0, 1]
- `keyword` — BM25 score, top-hit normalised to 1.0
- `score/10` — the memory's quality score (0–10), normalised
- `log_usage_norm = log2(1 + usage_count) / log2(1 + cap)` — usage frequency signal
- `decay = e^(-λ · days_since_last_used)` — time-decay so stale memories rank lower. `λ` defaults to `0.0077` (~90-day half-life), configurable via `LORE_DECAY_LAMBDA`. Set to `0` to disable. `last_used` updates on every retrieval; falls back to `created_at` if never retrieved

All weights are env-configurable via `LORE_W_*` vars (see `config.py`).

Semantic candidates: top 200 from Mem0. Keyword candidates: BM25. Both pools are unioned then re-ranked.

---

## `lore_insert`

```json
{
  "memories": [
    {
      "title": "Mutable default args in Python",
      "description": "def f(x=[]) shares the list across all calls — use None instead.",
      "content": "..."
    },
    {
      "title": "Token refresh interval",
      "content": "Access tokens expire after 1h.",
      "links": [
        {
          "target_memory_id": "<target-uuid>",
          "relation_type": "references",
          "reason": "part of OAuth flow"
        }
      ]
    }
  ],
  "links": [
    {
      "source_memory_id": "<uuid>",
      "target_memory_id": "<uuid>",
      "relation_type": "references",
      "reason": "Both about Python gotchas"
    }
  ],
  "force": false
}
```

Each memory dict:

| Field         | Required | Default | Description                                           |
| ------------- | -------- | ------- | ----------------------------------------------------- |
| `title`       | ✅       | —       | Short unique label for the memory                     |
| `content`     | —        | —       | Full text to store                                    |
| `description` | —        | —       | Brief summary                                         |
| `score`       | —        | `5.0`   | Initial quality score (0–10)                          |
| `links`       | —        | —       | Inline links to create after insert (see link schema) |

Top-level `links` (linking existing memories to each other) and per-memory inline `links` can be combined in one call.

### Duplicate detection

Before inserting, a dedup score is computed: `0.6·semantic + 0.4·keyword`. If it meets or exceeds `LORE_DUPLICATE_THRESHOLD` (default `0.85`), the insert is blocked and the existing memory is returned. Set `force: true` to bypass.

Note: `force=true` bypasses the semantic/keyword dedup check, but the DB still enforces `UNIQUE(namespace, title)` — inserting two memories with the same title in the same namespace will surface a constraint error in `errors[]`.

---

## `lore_remember`

```json
{
  "thought": "Hybrid search formula: 0.45 semantic + 0.30 keyword + 0.15 score + 0.10 usage"
}
```

Fast one-shot memory insert. Pass a single string; the server:

1. Auto-extracts the title (first ~80 chars, sentence boundary)
2. Stores the full content verbatim with default score `7.0`
3. Auto-links to the nearest semantic neighbor if similarity ≥ `0.75`

Returns `{id, title, linked_to: {id, score} | null}`.

Uses the same dedup pipeline as `lore_insert` — exact title matches are definitive duplicates.

Use `lore_remember` for quick capture. Use `lore_insert` when you need explicit titles, descriptions, scores, or manual links.

---

## `lore_update`

```json
{
  "memory_feedback": [{ "id": "<uuid>", "useful": true, "confidence": 8 }],
  "link_feedback": [{ "id": "<uuid>", "useful": false, "confidence": 3 }]
}
```

Drives the quality signal loop. Call after every `lore_search` to keep scores calibrated.

### Quality signal mechanics

Each feedback call:

- `useful=true` → score bumped up by `LORE_SCORE_BUMP_UP × (confidence/10)`
- `useful=false` → score bumped down by `LORE_SCORE_BUMP_DOWN × ((11-confidence)/10)`
- `useful=false` + `confidence ≤ 2` → memory is **soft-deleted** (never returned in future searches)

Confidence is stored as a running EMA over the last 20 ratings (`LORE_CONFIDENCE_WINDOW_SIZE`).

Unknown memory IDs are returned in `errors[]` — they do not raise exceptions.

---

## `lore_forget`

```json
{
  "memory_ids": ["uuid1", "uuid2"],
  "reason": "hallucinated"
}
```

Immediately soft-deletes one or more memories. The memories are excluded from `lore_search` results after this call.

`reason` must be one of: `duplicate`, `hallucinated`, `outdated`, `expired`, `unspecified`. Logged for auditability.

Soft-delete is reversible at the DB level, but no undelete tool is exposed via MCP.

Returns:

```json
{ "forgotten": [...], "not_found": [...], "errors": [...] }
```

---

## `lore_reflect`

```json
{
  "session_id": "uuid1",
  "summary": "Implemented reflect integration; extracted 3 lessons.",
  "session_date": "2026-05-19",
  "topic": "reflect-integration",
  "task_type": "build",
  "what_was_done": "Built the reflect integration...",
  "decisions": "- Used single-session submit for context efficiency",
  "lessons_learnt": ["Don't skip dedup check before inserting"],
  "good_patterns": ["Parallelise independent API calls"],
  "factual_discoveries": ["BM25 rebuild costs ~10ms at 5k memories"],
  "memory_ids": ["uuid-a", "uuid-b"],
  "auto_insert": true
}
```

Marks one session as processed and stores its content in the dashboard Sessions tab. Call once per session.

**Auto-insert (default `auto_insert=true`):** Each item in `factual_discoveries` and `lessons_learnt` is automatically inserted as a standalone searchable memory:

- `factual_discoveries` → score `7.0`, linked with `"discovered_in"` relation
- `lessons_learnt` → score `8.0`, linked with `"learned_in"` relation

Duplicate-guarded: items already in the store return `"status": "duplicate"` with the existing ID; new inserts return `"status": "inserted"`. Pass `auto_insert=false` to store only in the reflection record without creating memories.

**Idempotency:** If `session_id` was already processed, returns immediately with `"already_processed": true` and `"memories_created": []`. Check `already_processed` to detect retries.

Returns:

```json
{
  "reflection_id": "...",
  "session_id": "...",
  "created_at": "...",
  "memories_created": [
    {
      "id": "m-1",
      "title": "BM25 rebuild costs ~10ms...",
      "relation": "discovered_in",
      "status": "inserted"
    },
    {
      "id": "m-2",
      "title": "Don't skip dedup check...",
      "relation": "learned_in",
      "status": "inserted"
    }
  ]
}
```

---

## `lore_processed_sessions`

No parameters.

```json
{}
```

Returns all session IDs already marked as processed by `lore_reflect`. Use this to avoid re-processing sessions.

Returns:

```json
{ "session_ids": ["session-uuid-1", "session-uuid-2"] }
```

---

## `lore_recommend_links`

```json
{
  "lore_id": "<uuid>",
  "top_k": 10
}
```

Suggests link candidates between a memory and related memories. **Does not write any links** — returns candidates for review. Confirm by calling `lore_insert` with `links: [...]`.

Parameters:

- `lore_id` (required): source memory to find candidates for
- `top_k` (optional, default from `LORE_LINK_TOP_M`): max candidates to return

Scoring pipeline — semantic cosine, BM25, entity overlap, and temporal proximity combined into a per-signal weighted score.

Returns:

```json
{
  "candidates": [
    {
      "source_lore_id": "<uuid>",
      "target_lore_id": "<uuid>",
      "weighted_score": 0.65,
      "scores": {
        "cosine": 0.82,
        "bm25": 0.45,
        "entity": 0.0,
        "temporal": 0.0
      }
    }
  ],
  "count": 10,
  "source_lore_id": "<uuid>"
}
```

Per-signal `scores` let the agent make its own judgment about which candidates are worth linking — no LLM call inside Lorekeeper.

---

## `lore_get_suggestions`

List pending link suggestions generated by the background sweep engine.

```json
{
  "limit": 20,
  "min_score": 0.0
}
```

| Parameter   | Type    | Default | Description                               |
| ----------- | ------- | ------- | ----------------------------------------- |
| `limit`     | `int`   | `20`    | Max suggestions to return (capped at 100) |
| `min_score` | `float` | `0.0`   | Minimum `weighted_score` filter (0.0-1.0) |

**Response:**

```json
{
  "suggestions": [
    {
      "id": "uuid",
      "source_memory_id": "uuid",
      "target_memory_id": "uuid",
      "source_title": "...",
      "target_title": "...",
      "weighted_score": 0.87,
      "suggested_type": "references",
      "confidence": "high",
      "status": "pending"
    }
  ],
  "count": 1,
  "total_pending": 5
}
```

`total_pending` gives agents a sense of workload without a separate count call. Only `status='pending'` suggestions are returned regardless of the `min_score` filter.

---

## `lore_review_suggestion`

Accept or reject one or more link suggestions in a single call. Each item is processed independently — a failure on one does not abort the rest.

```json
{
  "suggestion_ids": ["uuid1", "uuid2"],
  "action": "accept"
}
```

| Parameter        | Type        | Description                  |
| ---------------- | ----------- | ---------------------------- |
| `suggestion_ids` | `list[str]` | One or more suggestion UUIDs |
| `action`         | `str`       | `"accept"` or `"reject"`     |

**On accept:** Creates a real `memory_links` row using the suggestion's `suggested_type` (falls back to `'references'` if None or unrecognised). The suggestion is retained with `status='accepted'` for audit trail.

**On reject:** Sets `status='rejected'` on the suggestion row. Future sweeps skip this pair.

**Idempotent:** Double-accept and double-reject both return `status='skipped'` — no error.

**Response:**

```json
{
  "results": [
    {
      "id": "uuid",
      "status": "accepted",
      "link_id": "uuid",
      "message": "Link created"
    }
  ],
  "accepted": 1,
  "rejected": 0,
  "skipped": 0,
  "errors": []
}
```

`status` per item is one of `"accepted"`, `"rejected"`, `"skipped"`, or `"error"`. `link_id` is the created link ID on accept, `null` on reject, skip, or error.

When `status="error"`, the item is also present in `errors[]` with the exception message. Callers iterating `results[*].status` should treat `"error"` as a failure sentinel and cross-reference `errors[]` for details.

---

## Environment Variables

All env vars use the `LORE_` prefix. Key configuration:

| Variable                      | Default         | Purpose                                                 |
| ----------------------------- | --------------- | ------------------------------------------------------- |
| `LORE_DATA_DIR`               | `~/.lorekeeper` | Where SQLite + vector DB live                           |
| `LORE_SEARCH_LIMIT`           | `10`            | Default max results from `lore_search`                  |
| `LORE_DUPLICATE_THRESHOLD`    | `0.85`          | Dedup block threshold (`0.6·semantic + 0.4·keyword`)    |
| `LORE_DECAY_LAMBDA`           | `0.0077`        | Time-decay rate (~90-day half-life). Set `0` to disable |
| `LORE_W_SEMANTIC`             | `0.45`          | Hybrid ranking: semantic weight                         |
| `LORE_W_KEYWORD`              | `0.30`          | Hybrid ranking: BM25 weight                             |
| `LORE_W_SCORE`                | `0.15`          | Hybrid ranking: quality score weight                    |
| `LORE_W_USAGE`                | `0.10`          | Hybrid ranking: usage frequency weight                  |
| `LORE_SCORE_BUMP_UP`          | `0.5`           | Score delta for `useful=true` feedback                  |
| `LORE_SCORE_BUMP_DOWN`        | `0.5`           | Score delta for `useful=false` feedback                 |
| `LORE_CONFIDENCE_WINDOW_SIZE` | `20`            | EMA window for running confidence score                 |
| `LORE_MAX_REFINE_FROM_IDS`    | `200`           | Max IDs accepted in `refine_from`                       |
| `LORE_MAX_SEARCH_IDS`         | `50`            | Max IDs accepted in `ids` (lookup mode)                 |
| `LORE_LINK_TOP_M`             | `10`            | Default max candidates from `lore_recommend_links`      |
| `LORE_NAMESPACE`              | `shared`        | Default namespace for writes                            |

Full list with types and defaults → `src/lorekeeper/config.py`.
