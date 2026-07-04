---
id: LKPR-106
title: Reduce lore_search default payload to critical fields only
type: feature
sprint: ~
rice_score: ~
filed_by: Jason
filed_date: 2026-07-04
github_issue: 276
---

# [LKPR-106] Reduce lore_search default payload to critical fields only

## Problem

The `lore_search` default (`format='full'`) returns a verbose payload per result — 12 memory fields, 4 relevance sub-scores, and a full links array. Most of this is noise for the agent:

**Memory fields** (12):

- `id`, `title`, `description`, `content` — essential
- `created_at`, `updated_at` — useful for recency-aware agents
- `score` — useful for ranking
- `source_type` — useful for provenance
- `soft_deleted`, `namespace`, `last_used`, `usage_count`, `confidence`, `confidence_count` — almost never used by agents

**Relevance** (4):

- `combined_score` — the only field the agent actually needs for ranking
- `semantic_score`, `keyword_score`, `decay_factor` — internal ranking signals, no agent value

Each result in `format='full'` costs ~300-500 tokens depending on content length and links. For a 3-result query, that's ~1,500 tokens of overhead — much of it noise fields the agent ignores.

LKPR-49 solved the sparse end (`format='title'` returns `{id, title, score}` at ~50 tokens), but the full format is still the default and still wasteful. Agents that want the full memory body shouldn't have to also receive fields they'll never use.

## Solution

Two options; Jason to decide:

**Option A — Prune the default**: Remove noise fields from `format='full'`:

- Strip: `soft_deleted`, `namespace`, `last_used`, `usage_count`, `confidence`, `confidence_count`
- Relevance: return only `combined_score`, drop `semantic_score`, `keyword_score`, `decay_factor`
- Links: keep but add `truncate_content` default (e.g., first 200 chars of content)
- Backwards-compat: add an `include_verbose` flag (default false) that restores all fields

**Option B — Add a `format='compact'` tier**: Keep `full` as-is for backward compat, add a middle tier:

- `"compact"` — returns `id`, `title`, `description`, `content` (truncated to 300 chars), `combined_score`, `created_at`, `source_type`. No links, no noise fields, no relevance breakdown.
- Two-call workflow becomes: `lore_search(..., format="title")` → pick → `lore_search(ids=[...])` ← already works ✓ or `lore_search(..., format="compact")` for a single richer pass

Option A is simpler (single format, less code, fewer knobs). Option B is safer (backward-compat).

## Acceptance Criteria

- [ ] `lore_search` default output excludes low-value fields (`soft_deleted`, `namespace`, `last_used`, `usage_count`, `confidence`, `confidence_count`)
- [ ] Relevance response excludes `semantic_score`, `keyword_score`, `decay_factor` by default
- [ ] Existing skills and callers that relied on removed fields continue working (either via a restore flag or by being updated)
- [ ] All existing tests pass — adjust assertions for the new default shape

## Affected Files

**Backend:**

- `src/lorekeeper/shared/serializers.py` — prune `serialize_search_result` default fields; add exclude set for noise fields
- `src/lorekeeper/api/mcp/handlers/memory_handlers.py` — pass `include_verbose` through if Option A chosen
- `src/lorekeeper/server.py` — update docstring for `lore_search` to reflect new default output shape
- `tests/test_handlers.py` — update assertions that check format='full' output shape

**Dashboard (if applicable):**

- `_none_` — dashboard has its own serialization path with different defaults

## Dependencies

- LKPR-49: Already done — the `format='title'` path is unaffected and continues to work
- LKPR-74: Observation type system — if merged, the type icon field should be included in the trimmed default

## Required Updates

- **CLAUDE.md**: [ ] Update `lore_search` default output description
- **README.md**: [ ] Document the new default shape and the `include_verbose` flag (if Option A)
- **Skills**: [ ] `lorekeeper-search` — verify it doesn't reference removed fields
- **Backlog**: [ ] N/A

## Open Questions

- Option A vs Option B?
- Should `content` also be truncated by default (e.g., first 500 chars) with the suggestion "use `ids` to fetch full content"?
- Is `soft_deleted` important enough to keep? It's almost always `false` in normal search (which already filters them out by default).

## Notes

Filed from Slack thread 2026-07-04 (Admin request). Corrected from LKPR-105 (collision with existing local file). Not a duplicate of LKPR-49 — that was about adding `format='title'` for the sparse end. This is about making the default format leaner so agents don't waste context budget on fields they never read. The two are complementary: `title` for fast listing, compact default for the main retrieval path.

Trade-off: backward incompatibility. The MCP tool is used by agents (not external API consumers), so breaking changes are manageable — skills can be patched. But if Jason prefers zero risk, Option B (new `format='compact'` tier) preserves backward compat.
