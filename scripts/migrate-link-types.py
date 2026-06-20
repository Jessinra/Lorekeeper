#!/usr/bin/env python3
"""Optional write-clean script for LKPR-67: Revise Link Relation Types.

PURPOSE
-------
This script rewrites old relation_type strings stored in the DB column to
their new canonical equivalents from the TYPE_MIGRATION_MAP. It is OPTIONAL
and NOT required for correctness — the read-side migration in
link_store._row_to_link already maps old types to new ones on every read.

Run this script only when you want to clean up the raw DB so that SELECT
queries against memory_links return new type strings directly (e.g. for
analytics, external tooling, or audit).

SAFETY
------
- Dry-run mode by default (shows what would change, makes no writes).
- Pass --apply to commit changes.
- Creates a backup SQLite file alongside the original before writing.
- Runs inside a single transaction; rolls back on any error.

USAGE
-----
    python scripts/migrate-link-types.py --db-path /path/to/lorekeeper.db
    python scripts/migrate-link-types.py --db-path /path/to/lorekeeper.db --apply

"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

TYPE_MIGRATION_MAP: dict[str, str] = {
    "related_to": "references",
    "used_in":    "part_of",
    "used_for":   "references",
    "used_by":    "depends_on",
    "used_as":    "references",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-path", required=True, type=Path,
        help="Path to the Lorekeeper SQLite database.",
    )
    parser.add_argument(
        "--apply", action="store_true", default=False,
        help="Write changes to DB (default: dry run).",
    )
    args = parser.parse_args()

    db_path: Path = args.db_path
    if not db_path.exists():
        print(f"ERROR: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Count affected rows per old type.
    print(f"\nScanning {db_path} ...\n")
    total = 0
    for old_type, new_type in TYPE_MIGRATION_MAP.items():
        rows = conn.execute(
            "SELECT COUNT(*) as cnt FROM memory_links WHERE relation_type=?",
            (old_type,),
        ).fetchone()
        count = rows["cnt"]
        if count:
            status = "s" if count != 1 else ""
            print(f"  {old_type!r:12s} -> {new_type!r:12s}  ({count} row{status})")
            total += count

    if total == 0:
        print("Nothing to migrate — no legacy relation_type strings found.")
        conn.close()
        return

    print(f"\nTotal rows to update: {total}")

    if not args.apply:
        print("\n[DRY RUN] No changes made. Pass --apply to commit.")
        conn.close()
        return

    # Backup before writing.
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    backup_path = db_path.with_suffix(f".{ts}.bak.db")
    print(f"\nCreating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    # Apply updates inside a single transaction.
    skipped = 0
    try:
        with conn:
            for old_type, new_type in TYPE_MIGRATION_MAP.items():
                cursor = conn.execute(
                    "UPDATE memory_links SET relation_type=? "
                    "WHERE relation_type=?",
                    (new_type, old_type),
                )
                updated = cursor.rowcount
                print(f"  {old_type!r:12s} -> {new_type!r:12s}  ({updated} updated)")
    except sqlite3.IntegrityError as exc:
        # UNIQUE constraint collision: a link with the target type already
        # exists for the same (source, target, relation_type) pair.
        print(f"  UNIQUE collision during update: {exc}")
        print("  Applying row-by-row fallback (skipping conflicts)...")

        conn.rollback()
        with conn:
            for old_type, new_type in TYPE_MIGRATION_MAP.items():
                rows = conn.execute(
                    "SELECT id,source_memory_id,target_memory_id "
                    "FROM memory_links WHERE relation_type=?", (old_type,),
                ).fetchall()
                for row in rows:
                    try:
                        conn.execute(
                            "UPDATE memory_links SET relation_type=? "
                            "WHERE id=?",
                            (new_type, row["id"]),
                        )
                    except sqlite3.IntegrityError:
                        skipped += 1
                print(f"  {old_type!r:12s} -> {new_type!r:12s}  done ({skipped} skipped)")
    except Exception as exc:
        print(f"ERROR during update — transaction rolled back: {exc}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    print(f"\nDone. Backup at {backup_path}")
    if skipped:
        print(f"  {skipped} row(s) skipped due to UNIQUE constraint conflicts "
              "(a link with the new type already exists).")

    conn.close()


if __name__ == "__main__":
    main()
