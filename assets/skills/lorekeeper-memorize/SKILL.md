---
name: lorekeeper-memorize
description: Memorize important facts, user instructions, unique discoveries, and interesting knowledge into the Lorekeeper knowledge base. Use proactively whenever the agent encounters noteworthy information — domain knowledge, user preferences, architectural decisions, debugging insights, workflow instructions, or any fact worth recalling in future sessions. Always searches for related memories and creates links between them.
version: 1.0.0
---

# Lorekeeper Memorize

Proactively capture valuable knowledge into Lorekeeper. Do not wait to be asked — memorize whenever something worth remembering surfaces.

## What to Memorize

- User instructions, preferences, "always do X" directives
- Domain knowledge, business rules, architecture decisions
- Debugging insights, root causes, non-obvious behaviour
- Interesting discoveries, undocumented behaviour, useful patterns
- Decisions and their rationale
- Team-specific jargon and definitions

**Skip**: Trivial facts, temporary context, or information already well-documented in the codebase.

## Workflow

### Step 1: Compose the memory

Write a standalone fact (must make sense without conversation context):

- **title**: Short label (max 100 chars)
- **description**: One-sentence summary (max 300 chars)
- **content**: Full detail (max 250 words). Be specific. Include the "why".

### Step 2: Search existing memories and provide feedback

Search for related memories. This is **mandatory** — even if you think nothing related exists.

```
lore_search({ query: "<topic of the new memory>", limit: 5, min_score: 0.2 })
```

Note which results are genuinely related (their `memory.id` values are needed for linking).

**Immediately** provide feedback on ALL returned results before proceeding:

```
lore_update({
  memory_feedback: [
    { id: "<id-1>", useful: true },
    { id: "<id-2>", useful: false }
  ]
})
```

Mark `useful: true` if the memory is related to the new fact. Mark `useful: false` if not. If zero results returned, skip this call.

### Step 3: Insert the memory

```
lore_insert({
  memories: [{
    title: "...",
    description: "...",
    content: "..."
  }]
})
```

Read the returned `inserted_memories[].id` from the response.

### Step 4: Link to related memories

If Step 2 found related memories, create links using the new memory's ID from Step 3:

```
lore_insert({
  links: [{
    source_memory_id: "<new-memory-id-from-step-3>",
    target_memory_id: "<related-existing-memory-id>",
    relation_type: "related_to",
    reason: "Why these are related"
  }]
})
```

Create one link per related memory. **Do not skip this step** — links are what make the knowledge graph useful.

### Relation types

| Type | Use when |
|------|----------|
| `related_to` | General topical relationship (default) |
| `used_in` | New fact is used within the existing memory's context |
| `used_for` | New fact serves a purpose described by the existing memory |
| `used_by` | New fact is consumed by the existing memory's concept |
| `used_as` | New fact acts as the existing memory's concept |

### Handling duplicates

If `lore_insert` returns a `duplicates` array, the memory was NOT inserted. Review the existing memory — if the new fact adds meaningful information, retry with `force: true`. Otherwise, skip.

## Reminders

- Be **proactive** — memorize whenever you spot something valuable
- Write **standalone facts** — no conversation context dependency
- **Always search first** — you may discover useful connections
- **Always link** — the knowledge graph depends on it
- **One fact per memory** — insert multiple memories for multiple facts
- **Feedback immediately** — call `lore_update` right after `lore_search`, before inserting
