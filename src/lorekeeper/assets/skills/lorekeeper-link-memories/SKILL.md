---
name: lorekeeper-link-memories
description: Discover and create typed relationships between memories using lore_recommend_links. Use after inserting new memories, after a session reflection, or during periodic maintenance to connect orphaned memories. Surfaces high-confidence link candidates scored by cosine similarity, BM25 keyword overlap, entity overlap, and temporal proximity. The agent decides which candidates to confirm — lore_recommend_links never writes.
version: v1.1.0
---

# Link Memories

Use `lore_recommend_links` to find high-confidence link candidates between memories, then confirm them via `lore_insert`.

## When to Run

- **After inserting a batch of memories** — new memories have few or zero links
- **After a session** — `lore_reflect` + `lore_insert` creates new facts; follow up with `lore_recommend_links` on key new memories
- **Periodic maintenance** — run `lore_recommend_links` on orphaned memories (those with `links: []` in search results)

## How to Use

```python
candidates = mcp_lore_recommend_links(lore_id="<memory-id>")
```

Optional `top_k` parameter overrides the max candidates returned.

## Reading the Output

Each candidate has:

- `weighted_score` (0.0–1.0): combined score from all 4 signals (cosine, BM25, entity overlap, temporal proximity)
- `scores`: per-signal breakdown for transparency

The agent evaluates candidates itself — it already has an LLM. `lore_recommend_links` only surfaces the data.

## What Makes a Good Link

- **Shared topic/entities**: memories about the same person, project, concept, or codebase
- **Causal or structural**: `depends_on` for dependencies, `references` for generic relations
- **Chronological**: `supersedes` for newer versions replacing older ones
- **Conflict**: `contradicts` when two memories make conflicting claims about the same thing

## What to Skip

- **Low weighted_score** (< 0.3): weak signals, likely spurious
- **Temporal-only matches**: memories created close in time but about completely different topics

## Confirming Links

`lore_recommend_links` **never writes anything**. To create a link:

```python
mcp_lore_insert(
    links=[{
        "source_memory_id": "<source-id>",
        "target_memory_id": "<target-id>",
        "relation_type": "references",
        "reason": "similar topic about Python web frameworks"
    }]
)
```

## Relation Types

| Type           | Meaning                                              |
| -------------- | ---------------------------------------------------- |
| `references`   | Mentions or cites — clean default for most links     |
| `depends_on`   | Requires or builds upon another memory               |
| `supersedes`   | Newer memory that replaces an older one              |
| `contradicts`  | Conflicting claims between memories                  |
| `part_of`      | Hierarchical composition — child belongs to parent   |
| `derived_from` | Based on, inferred from, or generalised from another |
| `causes`       | Direct causal relationship                           |
