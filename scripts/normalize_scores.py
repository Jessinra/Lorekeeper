#!/usr/bin/env python
"""
One-shot score normalization after raising the default insert score from 1.0 → 5.0.

All existing scores are shifted by +4.0 (capped at 10.0) so that memories inserted
under the old default sit at the new neutral baseline, and the relative ordering
from accumulated feedback is preserved.

Usage:
  uv run python scripts/normalize_scores.py [--dest ~/.lorekeeper] [--dry-run]
"""
import argparse
import sqlite3
from pathlib import Path

SHIFT = 4.0
SCORE_MAX = 10.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default=str(Path.home() / ".lorekeeper"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.dest) / "lorekeeper.db"
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, score FROM memories").fetchall()
    updates = [(min(SCORE_MAX, row["score"] + SHIFT), row["id"]) for row in rows]

    before = [r["score"] for r in rows]
    after  = [u[0] for u in updates]

    print(f"Memories to update : {len(rows)}")
    avg_before = sum(before) / len(before)
    print(f"Score range before : {min(before):.2f} - {max(before):.2f}  (avg {avg_before:.2f})")
    avg_after = sum(after) / len(after)
    print(f"Score range after  : {min(after):.2f} - {max(after):.2f}  (avg {avg_after:.2f})")
    print(f"Shift applied      : +{SHIFT}  (capped at {SCORE_MAX})")
    capped = sum(1 for a in after if a >= SCORE_MAX)
    if capped:
        print(f"Capped at {SCORE_MAX}      : {capped} memories")

    if args.dry_run:
        print("\n[dry-run] No changes written.")
        return

    conn.executemany("UPDATE memories SET score = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()
    print(f"\nDone. {len(updates)} scores updated in {db_path}")


if __name__ == "__main__":
    main()
