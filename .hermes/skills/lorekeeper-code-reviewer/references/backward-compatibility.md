# Backward Compatibility — BLOCKER Patterns

Lorekeeper has two hard backward compatibility contracts: stored data must never be lost or corrupted, and MCP tools must not break existing callers (agents, skills, dashboard).

## Data compatibility

- **Existing DB rows must survive the migration.** Any schema change must be tested against a copy of the current production DB. If a migration drops or corrupts data, it's a BLOCKER. Use `_rebuild_memory_links_table()` or `with conn:` — never raw `DROP TABLE` without verify-and-copy.

- **Old enum values in storage must not crash reads.** If you rename a relation type (`related_to` → `references`), the DB still holds old strings. The read path must normalize them: map old → new in `_row_to_link` or the lowest-level row reader. Unmapped old values hitting the serializer = BLOCKER.

- **DB CHECK constraints must accept legacy values.** When rebuilding a table with a new CHECK, list BOTH old and new values. `INSERT INTO new SELECT * FROM old` silently drops rows that violate the new CHECK — verify row counts match.

- **Default values for new columns must be no-ops.** A new column that silently changes existing behavior is a BLOCKER. Default to `None`, `False`, `""`, or whatever preserves the existing contract.

- **Write-cleanup scripts must be opt-in.** Shipped as `scripts/migrate-*.py` with `--dry-run` as default. Never auto-run on server start.

## API compatibility

- **Tool name, inputs, and output shapes must not break.** Existing agents load `lore_search`, `lore_remember`, `lore_insert`, `lore_update`, `lore_forget`, `lore_recommend_links`. Renaming, dropping inputs, or changing response keys breaks every installed agent and shipped skill. If a rename is necessary, keep the old name as a deprecated alias for one release cycle.

- **New optional fields don't change default return shape.** Adding a field to search responses is fine — making it required so existing callers crash is not. New fields must be `None` or absent by default.

- **Shipped skills must still work.** If your PR changes a tool output field name, grep every shipped skill in `src/lorekeeper/assets/skills/`. A stale reference = users get errors. (This was caught in LKPR-67 review.)

- **Config env vars are API too.** `LORE_*` env vars are the user-facing configuration surface. Renaming or removing one without a deprecation cycle is a BLOCKER. Log a warning for one release before removal.

- **Import paths in the Python API are API.** Public symbols from `lorekeeper.xxx` are part of the surface. Renaming a module without a backward-compat alias = breakage.

## How to check during review

```bash
# 1. Shipped skills still reference old types?
grep -rn '"related_to"\|"used_in"\|"used_for"\|"used_by"\|"used_as"' src/lorekeeper/assets/skills/

# 2. CHECK constraint backward compat?
# grep the migration for the CHECK — does it list ALL old values?

# 3. Any env var removal?
grep -rn "LORE_DEPRECATED\|LORE_REMOVED" src/lorekeeper/ docs/

# 4. Shipped skill references to changed tool/param?
grep -rn "tool_name\|new_param_name" src/lorekeeper/assets/skills/
```

## Migration compatibility checklist

Every migration PR must confirm:

- [ ] All existing data survives: old rows → new schema → same row count
- [ ] Old enum values normalized on read via mapping, or accepted by CHECK constraint
- [ ] Read path handles unmapped values gracefully (safe sentinel, doesn't crash)
- [ ] Shipped skills updated if tool output shape changed
- [ ] Rollback path documented
- [ ] No silent data loss: row count matches pre-migration
- [ ] Default for new columns is backward-compatible (no-op for existing callers)
- [ ] Config env vars not removed without deprecation cycle
