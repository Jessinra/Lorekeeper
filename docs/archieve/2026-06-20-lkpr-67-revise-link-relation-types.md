# LKPR-67 — Revise Link Relation Types

**Date:** 2026-06-20
**Ticket:** backlogs/ready/LKPR-67-revise-link-relation-types.md
**Approach:** Read-side migration (zero-downtime) + write-time rejection of old types

---

## Summary of Change

Replace 8 old relation types (`related_to`, `used_in`, `used_for`, `used_by`, `used_as`, `contradicts`, `supersedes`, `depends_on`) with 7 new types (`references`, `depends_on`, `supersedes`, `contradicts`, `part_of`, `derived_from`, `causes`).

**Carry-overs:** `contradicts`, `supersedes`, `depends_on` are semantically unchanged — just remain valid.
**Removed:** `related_to`, `used_in`, `used_for`, `used_by`, `used_as`
**Added:** `references`, `part_of`, `derived_from`, `causes`

**Migration strategy:** Read-side mapping on load — no column rewrite. Old type strings stored in DB are transparently mapped when read back. New writes reject old types.

---

## Migration Map

```python
TYPE_MIGRATION_MAP = {
    "related_to": "references",  # catch-all → default
    "used_in":    "part_of",     # "used in X context" → compositional
    "used_for":   "references",  # "used for purpose" → reference
    "used_by":    "depends_on",  # "used by Y" → inverse dependency
    "used_as":    "references",  # "used as tool" → reference
}
```

Entries NOT in this map (`contradicts`, `supersedes`, `depends_on`) are carried over unchanged — they are valid in both old and new sets.

---

## Per-File Change Breakdown

### 1. `src/lorekeeper/models.py`

- **Replace** `RelationType` Literal: remove 5 old types, keep 3 survivors, add 4 new
- **Add** `TYPE_MIGRATION_MAP: dict[str, str]` constant
- **No changes** to `RELATION_TYPES` frozenset logic (auto-derives from the updated Literal)

**New RelationType literal:**

```python
RelationType = Literal[
    "references",    # mentions or cites — default for most links
    "depends_on",    # requires or builds upon
    "supersedes",    # newer memory that replaces an older one
    "contradicts",   # content conflicts
    "part_of",       # hierarchical composition
    "derived_from",  # based on / inferred from
    "causes",        # direct causal link
]
```

### 2. `src/lorekeeper/services/database.py`

- **Add `_migration_4_revise_relation_types`** — rebuilds `memory_links` table with updated CHECK constraint including all 7 new types plus the 5 legacy types (so existing rows aren't rejected during data copy). Legacy types remain in DB storage; read-side mapping handles display.
- **Append to `MIGRATIONS`** list: `(4, "revise_relation_types", _migration_4_revise_relation_types)`
- The new CHECK constraint accepts both old AND new strings (for backward compat of existing rows). Write-time validation (in orchestrator/models) is the wall that blocks new old-type writes.

**New CHECK constraint string (all 12 values):**

```sql
CHECK (relation_type IN (
  'references','depends_on','supersedes','contradicts','part_of','derived_from','causes',
  'related_to','used_in','used_for','used_by','used_as'
))
```

Note: we keep old values in CHECK so the table-rebuild migration copies them cleanly. Write-side validation in orchestrator will block new uses.

- **Update `BASE_SCHEMA`**: change the `memory_links` CHECK constraint to include all 12 values (so fresh installs get a permissive constraint, with application-layer enforcement doing the real work).

### 3. `src/lorekeeper/services/orchestrator.py`

- **Import `TYPE_MIGRATION_MAP`** from `models`
- **Update `_validate_relation_type`**: accepts ONLY the 7 new types (uses `RELATION_TYPES` which derives from the updated Literal). Old types now raise ValueError at write time.
- **Add `_normalize_relation_type` helper**: applies `TYPE_MIGRATION_MAP` on read. If type not in map, return as-is (covers the 3 surviving unchanged types).
- **Apply mapping in `_auto_link`**: change hardcoded `"related_to"` → `"references"` (the new default).
- **Apply mapping on link reads**: in `search()` / `search_by_ids()`, after fetching links via `links_for_memory()`, normalize each link's `relation_type` before returning in `SearchResult`. Practically: patch the `MemoryLink` objects or normalize in `_row_to_link` — see below.
- **No changes to `import_dump`**: it bypasses `_validate_relation_type` and calls `insert_link` directly — we add a pass-through note that old types stored in DB are valid for import restore.

**Where to apply the read mapping:** The cleanest place is `link_store.py`'s `_row_to_link` function. Normalizing there means every caller (search, links_for_memory, all_links) gets mapped values transparently.

### 4. `src/lorekeeper/services/link_store.py`

- **Update `_row_to_link`**: apply `TYPE_MIGRATION_MAP` to `row["relation_type"]` before constructing `MemoryLink`. Import `TYPE_MIGRATION_MAP` from `models`.
- No other changes — storage is string, constraint is in DB.

### 5. `src/lorekeeper/dashboard/routes/links.py`

- **`LinkCreate.relation_type`**: typed as `RelationType` — will automatically reject old types since `RelationType` Literal is updated. No code change needed.
- Verify the auto-validation works correctly (covered by test).

### 6. `scripts/migrate-link-types.py` (new file)

- Optional write-migration script for users who want to clean their DB.
- Reads all links, applies `TYPE_MIGRATION_MAP`, writes back changed rows.
- Has `--dry-run` flag.
- Not required to pass tests; ships as a utility.

---

## DB Migration Details (`_migration_4_revise_relation_types`)

Uses the same table-rebuild pattern as migration 2:

1. Check idempotency (if `memory_links_old` exists, skip rename)
2. Rename `memory_links` → `memory_links_old`
3. `CREATE TABLE IF NOT EXISTS memory_links` with updated CHECK (12 values)
4. `INSERT OR IGNORE INTO memory_links SELECT * FROM memory_links_old`
5. Drop `memory_links_old`
6. Recreate indexes (`idx_links_source`, `idx_links_target`, `idx_links_unique_pair`)

---

## Test Changes

### `tests/test_database.py`

- **Update migration version assertions**: two tests check `current_version() == 3` → update to `== 4`
  - `test_migrate_applies_bootstrap_to_fresh_db`: assert `== 4`
  - `test_migrate_rolls_back_on_failure_and_does_not_record_version`: the baseline `db.migrate()` call now lands at `== 4`; injected failing migration is `(5, ...)` not `(4, ...)` — update assertion
- **Add `test_migration_4_revise_relation_types`**:
  - Build DB, apply migrations 1–3 manually, seed link with `related_to`
  - Apply `_migration_4_revise_relation_types`
  - Assert existing `related_to` row survived
  - Assert new types (`references`, `part_of`, `derived_from`, `causes`) are accepted
  - Assert old type `related_to` is still accepted in DB (write-side rejects it, DB allows it for legacy rows)
  - Call migration twice — no exception (idempotency)
- **Add `test_relation_type_migration_map`**: imports `TYPE_MIGRATION_MAP`, asserts all 5 old types present, all values are valid new types

### `tests/test_link_store.py`

- **Update `test_links_for_memory_bidirectional`**: changes `"used_in"` → `"part_of"` (new type), since `_row_to_link` now normalizes on read. Or keep `"used_in"` in storage and assert the returned link has `"part_of"` — whichever demonstrates the mapping.

### `tests/test_orchestrator.py` (or new `tests/test_lkpr67_relation_types.py`)

- **`test_validate_relation_type_rejects_old_types`**: call `_validate_relation_type("related_to")` → `ValueError`
- **`test_validate_relation_type_accepts_new_types`**: all 7 new types pass
- **`test_auto_link_uses_references_type`**: insert a memory, trigger auto-link, verify link has `relation_type="references"` (not `"related_to"`)
- **`test_read_side_mapping_applied`**: insert link with raw `related_to` via `insert_link` (bypasses orchestrator validation), then `links_for_memory` → assert `relation_type == "references"`

### `tests/test_handlers.py`

- Line 265: change `"related_to"` → `"references"` (the new valid default type)

---

## CLAUDE.md & Docs Updates

- **No CLAUDE.md changes needed** — no RelationType docs in CLAUDE.md (confirmed via grep)
- **README.md** — add a note about the new 7-type set and migration map under the Links section (per ticket ACs)
- **Skills** — update `lorekeeper-dev` skill: link relation types section; `lorekeeper-search` if it mentions types

---

## Execution Order

1. `models.py` — types + migration map
2. `link_store.py` — `_row_to_link` mapping
3. `orchestrator.py` — validation update + auto_link default
4. `database.py` — migration 4 + update BASE_SCHEMA
5. Tests — update existing, add new
6. `scripts/migrate-link-types.py` — optional script
7. README.md update
8. `uv run pytest -v` — full suite green
9. Branch, commit, PR

---

## Risks

- **Unique pair index**: old type and new type for same pair can coexist in DB (e.g. `related_to` and `references` for same source/target). The read-side map makes both look like `references`, but the unique index only blocks exact-string duplicates. Low risk in practice — existing links use old strings, new writes use new strings, no collision. If users run the optional migration script, exact-string dupes can be created by the mapping; the script should handle that (dedup before upsert).
- **import_dump bypass**: the import path calls `insert_link` directly with the relation_type from the dump. Old dumps with `used_in` etc. will be stored as-is (CHECK allows it), and mapped on read. Correct behavior.
