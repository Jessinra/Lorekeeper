"""Seed LanceDB from existing Chroma/SQLite data.

Usage:
    uv run python scripts/seed_lancedb.py

This reads all memories from SQLite, embeds them, and inserts into LanceDB.
Chroma data is left untouched — no migration needed, memories survive via SQLite.
"""
import os
import sys

os.environ.setdefault("MEM0_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

# Ensure we're in the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lorekeeper.config import Settings
from lorekeeper.services.database import Database
from lorekeeper.services.engine_factory import build_engine
from lorekeeper.services.memory_store import MemoryStore


def main() -> None:
    s = Settings()
    db = Database(s.sqlite_path)
    db.migrate()
    memories = MemoryStore(db)
    rows = memories.all_memory_rows(include_deleted=True)

    if not rows:
        print("No memories found in SQLite — nothing to seed.")
        return

    print(f"Found {len(rows)} memories in SQLite. Seeding LanceDB at {s.lancedb_path}...")

    engine = build_engine("lancedb", s.chroma_path, s.lancedb_path, s.embedding_model)
    inserted = 0
    for row in rows:
        lore_id = row["id"]
        text = " ".join(
            filter(None, [row["title"] or "", row["description"] or "", row["content"] or ""])
        )
        if not text.strip():
            print(f"  Skipping {lore_id} — empty text")
            continue
        engine.add(text.strip(), lore_id)
        inserted += 1
        if inserted % 20 == 0:
            print(f"  {inserted}/{len(rows)}...")

    total = len(engine.get_all())
    print(f"\nDone. Inserted {inserted} memories. LanceDB has {total} total entries.")


if __name__ == "__main__":
    main()
