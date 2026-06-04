# Link Memories (lorekeeper-link-memories)

Use `lore_recommend_links` to find high-confidence link candidates between memories, then confirm them via `lore_insert`.

## When to Run

- **After inserting a batch of memories** — new memories have few or zero links
- **After a session** — `lore_reflect` + `lore_insert` creates new facts; follow up with `lore_recommend_links` on key new memories
- **Periodic maintenance** — run `lore_recommend_links` on orphaned memories (those with `links: []` in search results)
- **Before using `lore_related`** — `lore_related` only returns memories with explicit links; run `lore_recommend_links` first if the graph is sparse

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
- **Causal or structural**: "depends_on" for dependencies, "used_in" for implementation details
- **Chronological**: "supersedes" for newer versions replacing older ones
- **Conflict**: "contradicts" when two memories make conflicting claims about the same thing

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
        "relation_type": "related_to",
        "reason": "similar topic about Python web frameworks"
    }]
)
```

## Relation Types

| Type | Meaning |
|------|---------|
| `related_to` | General thematic connection (default) |
| `used_in` | Source concept is used in target context |
| `used_for` | Source is used for the purpose in target |
| `used_by` | Source is used by entity in target |
| `used_as` | Source serves as a role in target |
| `contradicts` | Conflicting claims between memories |
| `supersedes` | Source replaces/updates target |
| `depends_on` | Source requires or builds upon target |