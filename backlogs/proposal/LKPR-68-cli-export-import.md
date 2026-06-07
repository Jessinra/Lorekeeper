---
id: LKPR-68
title: CLI export/import for headless backup and restore
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 149
filed_date: 2026-06-06
---

# [LKPR-68] CLI export/import for headless backup and restore

## Problem

Currently, Lorekeeper backup and restore is only available through the dashboard UI (Backup tab). This leaves three critical gaps:

1. **Cron jobs and scripts** — no way to schedule automated backups (daily/weekly dumps to cold storage)
2. **Headless agents** — Hermes agents running without a dashboard can't back up or restore their memory store
3. **Machine-to-machine transfer** — migrating memory between instances requires the full dashboard stack just to produce/consume a JSON file

LKPR-32 (encrypted backup/restore) exists in proposal but is dashboard-first with encryption complexity. What's missing is the simplest possible CLI that produces a portable dump of all data.

## Solution

Add two new CLI subcommands to the existing `lorekeeper` entrypoint:

### `lorekeeper export`

Dumps all Lorekeeper data (memories, links, reflections, sessions, config overrides) to a single JSON file.

```
lorekeeper export --output /path/to/backup-2026-06-06.json
```

- Includes: all memory rows (including soft_deleted), all links, all reflections, all sessions, all config_overrides
- Vector store is **excluded** — on import, embeddings are regenerated from memory text (Chroma/LanceDB handles this on insert)
- Format: a simple JSON object with top-level keys per table (same as the dashboard export API produces)
- Metadata: includes `lorekeeper_version` and `exported_at` timestamp for compatibility checks
- `--pretty`: human-readable formatting (default: compact)
- `--stdout`: print to stdout instead of file (pipe-compatible)

### `lorekeeper import`

Loads a previously exported dump into the current data directory.

```
lorekeeper import --input /path/to/backup-2026-06-06.json
```

- Destructive by default — replaces all existing data with the imported dump
- `--merge`: inserts/replaces records by ID, keeping records that exist in both
- `--dry-run`: validates the file format + reports record counts without writing
- Compatible with dashboard-exported files (both use the same JSON schema)

### `lorekeeper export --format jsonl`

Stretch goal: JSONL output (one memory per line) for streaming, differential backups, and pipe-to-tools workflows.

## No encryption in v1

Plain JSON only. Encryption (Fernet) belongs in LKPR-32 if/when it's prioritised. The CLI is for local/trusted environments — cron dumps to an S3 bucket, agent migrations, dev-to-prod seeding. If users need encryption, they wrap the CLI: `lorekeeper export --stdout | gpg --encrypt`.

## Acceptance Criteria

- [ ] `lorekeeper export --output backup.json` produces a valid JSON file with all tables
- [ ] `lorekeeper export --stdout` prints the JSON to stdout
- [ ] `lorekeeper import --input backup.json` fully restores the data store
- [ ] `lorekeeper import --merge` merges records by ID (inserts if not present, updates if exists)
- [ ] `lorekeeper import --dry-run` validates and reports counts without writing
- [ ] Import regenerates embeddings for all memories (vector store doesn't need separate backup)
- [ ] Import supports the same JSON schema as the dashboard export API (interoperable)
- [ ] `--help` output documents all subcommand flags
- [ ] Exported file includes `lorekeeper_version` for forward-compatibility checks
- [ ] Importing a file with an incompatible version produces a clear error

## Affected Files

**Backend:**

- `src/lorekeeper/cli/__init__.py` — add `export` and `import` subcommands to `typer`/`click` CLI
- `src/lorekeeper/cli/export.py` (new) — `export_cmd()`: dumps all stores to JSON
- `src/lorekeeper/cli/import_cmd.py` (new) — `import_cmd()`: validates + loads JSON into stores
- `src/lorekeeper/services/serializers.py` — reuse or extend existing dump/load logic (LKPR-43)
- `pyproject.toml` — add `typer` or `click` to deps if not already present

**Dashboard (if applicable):**

- `_none_` — CLI is independent of dashboard

## Dependencies

LKPR-43 (shared serializer) — the dashboard export/import should already use shared serialization code that this CLI can reuse. If LKPR-43 isn't merged, this ticket should align with whatever serializers exist.

## Required Updates

- **CLAUDE.md**: [ ] Document CLI export/import subcommands
- **README.md**: [ ] Add CLI section with export/import examples
- **Skills**: [ ] `lorekeeper-server` — add export/import to restart checklist; `daily-reflection-cron` — consider adding automatic backup step
- **Backlog**: [ ] N/A

## Open Questions

- Should the export include the entire vector store (serialised embeddings), or regenerate on import? Regenerate is preferred — embeddings are large, LLM-generated sources change, and regeneration is cheap with the embedding model already running.
- Should the merge strategy be last-write-wins or skip-if-older? Last-write-wins is simpler and matches expected behaviour for backup restore.
- What about config overrides? Include them in the dump since they affect behaviour.
- Should we add `lorekeeper info` (stats about the current store) while we're in the CLI? No — scope creep.

## Notes

Filed alongside LKPR-67 (relation type revision) as a pair of backlog cleanup tickets. This addresses the "how do I back up without the dashboard" gap that's come up in the reflection pipeline (current cron uses `hermes sessions export` as a workaround).

Not a replacement for LKPR-32 (encrypted backup) — that ticket adds encryption on top of whatever export pipeline exists. This ticket builds the plain-text CLI foundation that LKPR-32 could later encrypt.

Key design principle: the export format should be identical to what the dashboard export produces, so both paths are interoperable. Users can export via CLI, import via dashboard, or vice versa.
