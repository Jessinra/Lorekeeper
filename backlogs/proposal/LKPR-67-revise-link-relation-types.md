---
id: LKPR-67
title: Revise link relation types for clarity and coverage
type: enhancement
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 148
filed_date: 2026-06-06
superseded_by: LKPR-98
---

# [LKPR-67] Revise link relation types for clarity and coverage

## Problem

The current 8 link relation types have overlapping semantics that make consistent use impossible:

- `related_to` is a catch-all default used everywhere because nothing else fits — makes the type field meaningless
- The usage family (`used_in`, `used_for`, `used_by`, `used_as`) has no clear semantic boundary. What distinguishes "used_in" from "used_for"? Different agents pick different ones for the same relationship
- Missing common relationship types like causal links, part-whole, derivative, and reference
- `lore_recommend_links` (LKPR-58) will suggest types — but with the current ambiguous set, suggestions will be unreliable

Feedback scores on existing link type usage show low confidence (most links have 0 confidence feedback), suggesting the current types aren't being used meaningfully.

## Solution

Replace the current 8 types with a smaller, clearer set. Each type has one obvious meaning:

| Type           | Meaning                                                     | Example                                                      |
| -------------- | ----------------------------------------------------------- | ------------------------------------------------------------ |
| `references`   | Mentions or cites — clean default for most links            | Memo about "Prompt caching" references "Claude API docs"     |
| `depends_on`   | Requires or builds upon another memory                      | "Auth middleware" depends_on "JWT token format"              |
| `supersedes`   | Newer memory that replaces an older one                     | "v2 API spec" supersedes "v1 API spec"                       |
| `contradicts`  | Content conflicts with another memory                       | "Benchmark A shows X" contradicts "Benchmark B shows X"      |
| `part_of`      | Hierarchical composition — child belongs to parent          | "Login page" part_of "Auth module"                           |
| `derived_from` | Based on, inferred from, or generalized from another memory | "User retention pattern" derived_from "Cohort analysis data" |
| `causes`       | Direct causal relationship                                  | "Rate limit change" causes "Increased error 429 reports"     |

That's 8 → 7, but every type is distinct and self-evident.

**Existing links migration:** links with old types are mapped to the closest new type on read (no rewrite needed if we store a simple mapping). See migration plan below.

## Acceptance Criteria

- [ ] `models.py` `RelationType` literal updated to 7 new types
- [ ] `RELATION_TYPES` frozenset updated in `models.py` (auto-derives from the literal)
- [ ] DB migration (version N) adds `relation_type_v2` column and populates via mapping — or applies a read-side mapping so old links render correctly without a blocking write migration
- [ ] `lore_recommend_links` candidate generation updated to suggest the new types
- [ ] Dashboard link display renders correctly for both old and new types
- [ ] All existing tests pass; new tests added for old-type→new-type mapping
- [ ] CLI/API validation rejects old types on new `lore_insert` or `lore_recommend_links` feedback

## Read-side migration (preferred approach)

Rather than a blocking column-rewrite migration (which would scan 100% of existing links), use a read-side mapping:

```python
# In orchestrator.py or models.py
TYPE_MIGRATION_MAP = {
    "related_to": "references",  # catch-all → default
    "used_in": "part_of",        # "used in X context" → compositional
    "used_for": "references",    # "used for purpose" → reference
    "used_by": "depends_on",     # "used by Y" → inverse dependency
    "used_as": "references",     # "used as tool" → reference
}
```

- On link CRUD reads: if type is in old set, return the mapped value
- On `lore_insert` / new links: old types are rejected with a clear error message
- A background migration script (`scripts/migrate-link-types.py`) is provided for users who want to write-clean their DB, but is optional — the read-side mapping is the default

This keeps the upgrade zero-downtime and avoids touching 100% of rows for every user on upgrade.

## Affected Files

**Backend:**

- `src/lorekeeper/models.py` — `RelationType` literal, migration map
- `src/lorekeeper/services/orchestrator.py` — type validation + recommend_links type generation
- `src/lorekeeper/services/link_store.py` — no changes (stores string; validation happens at orchestrator)
- `src/lorekeeper/services/database.py` — add migration entry
- `scripts/migrate-link-types.py` (new) — optional write-migration script

**Dashboard:**

- `src/lorekeeper/dashboard/static/js/links.js` — update type display labels if hardcoded
- `src/lorekeeper/dashboard/routes/links.py` — ensure any type validation matches orchestrator

## Dependencies

LKPR-58 (smart link candidate pipeline) — this ticket should be sequenced after or in parallel with LKPR-58, since LKPR-58 will suggest relation types and we want it suggesting the new, clean set.

## Required Updates

- **CLAUDE.md**: [ ] Update RelationType docs
- **README.md**: [ ] Document new types and migration mapping
- **Skills**: [ ] `lorekeeper-search` — update type descriptions; `memory-linker` — update type set
- **Backlog**: [ ] N/A

## Open Questions

- Should the migration map be hardcoded or env-configurable? (Hardcoded is simpler — if users disagree with a mapping, they can edit links manually)
- Do we need a `lore_update_link` tool to let agents change a link's type? Not for this ticket — can be follow-up
- Should we keep `related_to` as a valid but deprecated type that warns on use? (Yes — softer transition than hard-rejection)

## Notes

Filed from PM review of link system quality. The usage family (`used_*`) is the main pain point — four types that mean nearly the same thing. The new 7-type set aims for "argue about which type less than 5 seconds" clarity. If it turns out even 7 is too many, `causes` and `derived_from` could merge (both causal/derivative), keeping 6.
