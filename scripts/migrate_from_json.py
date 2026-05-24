#!/usr/bin/env python
"""
One-shot migration from lorekeeper v1 (memories.json) to v2 (Mem0 + SQLite).

Usage:
  uv run python scripts/migrate_from_json.py \
    --source /path/to/memories.json \
    --dest   ~/.lorekeeper
    [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lorekeeper.config import Settings
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_engine import ChromaDBEngine, build_mem0


def load_source(path: Path) -> tuple[list[dict], list[dict]]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        mems = data.get("memories", [])
        links = data.get("links", [])
        if isinstance(mems, dict):
            mems = list(mems.values())
    else:
        mems = data
        links = []
    return mems, links


def migrate(source: Path, dest: Path, dry_run: bool) -> None:
    mems, links = load_source(source)
    print(f"Source: {len(mems)} memories, {len(links)} links")

    settings = Settings(data_dir=dest)
    dest.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print("[dry-run] would migrate to:", dest)
        return

    print("Loading Mem0 + Chroma (first run downloads model ~90 MB) ...")
    mem0 = build_mem0(settings.chroma_path, settings.embedding_model)
    engine = ChromaDBEngine(mem0)

    store = LinkStore(settings.sqlite_path)

    # Get already-migrated lore_ids for idempotency
    existing = {e["lore_id"] for e in engine.get_all()}
    print(f"Already in Chroma: {len(existing)}")

    inserted = 0
    skipped = 0
    for m in mems:
        lore_id = m["id"]
        if lore_id in existing:
            skipped += 1
            continue

        text = f"{m['title']} {m.get('description', '')} {m.get('content', '')}"
        engine.add(text, lore_id)
        store.upsert_memory_row(
            id=lore_id,
            title=m["title"],
            description=m.get("description", ""),
            content=m.get("content", ""),
            created_at=m.get("created_at", ""),
            updated_at=m.get("updated_at", ""),
            usage_count=m.get("usage_count", 0),
            score=float(m.get("score", 1.0)),
            soft_deleted=bool(m.get("soft_deleted", False)),
            confidence=m.get("confidence"),
            confidence_count=int(m.get("confidence_count", 0)),
        )
        inserted += 1
        if inserted % 10 == 0:
            print(f"  {inserted}/{len(mems) - skipped} memories embedded...")

    print(f"Memories: {inserted} inserted, {skipped} already existed")

    # Migrate links — skip if either FK is missing
    link_inserted = 0
    link_skipped = 0
    for lnk in links:
        src = lnk.get("source_memory_id") or lnk.get("sourceMemoryId")
        tgt = lnk.get("target_memory_id") or lnk.get("targetMemoryId")
        rel = lnk.get("relation_type") or lnk.get("relationType", "related_to")
        reason = lnk.get("reason", "")
        score = float(lnk.get("score", 1.0))

        if not src or not tgt:
            link_skipped += 1
            continue
        if store.get_memory_row(src) is None or store.get_memory_row(tgt) is None:
            link_skipped += 1
            continue

        try:
            store.insert_link(src, tgt, rel, reason, score)
            link_inserted += 1
        except Exception as e:
            print(f"  link skip ({src}→{tgt}): {e}")
            link_skipped += 1

    print(f"Links: {link_inserted} inserted, {link_skipped} skipped")

    # Rebuild BM25
    from lorekeeper.models import Memory
    all_rows = store.all_memory_rows(include_deleted=True)
    kw = KeywordIndex()
    kw.rebuild([
        Memory(
            id=r["id"], title=r["title"], description=r["description"],
            content=r["content"], created_at=r["created_at"], updated_at=r["updated_at"],
            usage_count=r["usage_count"], score=r["score"],
            soft_deleted=bool(r["soft_deleted"]),
            confidence=r["confidence"], confidence_count=r["confidence_count"],
        )
        for r in all_rows
    ])
    print(f"BM25 index rebuilt over {len(all_rows)} memories")
    print("Migration complete.")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--dest", required=True, type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    migrate(args.source, args.dest, args.dry_run)


if __name__ == "__main__":
    main()
