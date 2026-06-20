#!/usr/bin/env python3
"""Periodic link suggestion sweep — callable from cron/systemd or manual.

Usage:
    python scripts/sweep-links.py              # uses default data dir
    python scripts/sweep-links.py --data-dir ~/.lorekeeper/profile/diana
    python scripts/sweep-links.py --dry-run    # no writes
    python scripts/sweep-links.py --help
"""

import argparse
import sys
from pathlib import Path

from lorekeeper.config import Settings
from lorekeeper.services.config_store import ConfigStore
from lorekeeper.services.database import Database
from lorekeeper.services.engine_factory import build_engine
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.orchestrator import MemoryService
from lorekeeper.services.reflection_store import ReflectionStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Link suggestion sweep engine")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Data directory (default: Settings().data_dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run sweep logic but skip all writes",
    )
    args = parser.parse_args()

    settings = Settings()
    if args.data_dir:
        settings.data_dir = args.data_dir

    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Data dir: {data_dir}")
    print(f"Dry run:  {args.dry_run}")

    # Build engine via factory (handles abstract class)
    engine = build_engine(settings.lancedb_path, settings.embedding_model)
    engine.probe_score_scale()

    # Build stores
    db = Database(settings.sqlite_path)
    db.migrate()

    memories = MemoryStore(db)
    links = LinkStore(db)
    reflections = ReflectionStore(db)
    metrics = MetricsStore(db)
    config = ConfigStore(db)

    kw = KeywordIndex()
    svc = MemoryService(
        engine, memories, links, db, reflections, metrics, config, kw, settings
    )

    # Bootstrap BM25
    all_mems = list(svc._all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    print(f"BM25 rebuilt with {len(all_mems)} memories")

    if args.dry_run:
        print("\nDry-run mode: scanning only, no writes.")
        all_active = svc._all_memories(include_deleted=False)
        print(f"Active memories to scan: {len(all_active)}")
        total_candidates = 0
        for mem_id in list(all_active.keys())[:10]:  # sample first 10
            try:
                candidates = svc._link_candidate_generator.generate(mem_id)
                total_candidates += len(candidates)
            except Exception as e:
                print(f"  {mem_id}: error - {e}")
        print(f"Total candidates (first 10 memories): {total_candidates}")
        print("Dry run complete.")
    else:
        stats = svc.sweep_links()
        print("\nSweep complete:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
