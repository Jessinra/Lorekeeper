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

from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.models import Memory
from lorekeeper.services.link_candidate import LinkCandidateGenerator
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.suggestion_store import LinkSuggestionStore
from lorekeeper.services.sweep_service import SweepService


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

    # Build engine directly — no factory needed after LKPR-103 (ABC removed)
    engine = LanceDBEngine(settings.lancedb_path, settings.embedding_model)
    engine.probe_score_scale()

    # Build stores
    db = Database(settings.sqlite_path)
    db.migrate()

    memories = MemoryStore(db)
    links = LinkStore(db)
    metrics = MetricsStore(db)

    # Namespace filter: shared agents see everything
    ns_filter: list[str] | None = (
        None if settings.namespace == "shared" else [settings.namespace, "shared"]
    )

    # One shared LinkCandidateGenerator (spaCy loaded once)
    kw = KeywordIndex()
    link_candidate_generator = LinkCandidateGenerator(
        engine=engine,
        memory_store=memories,
        link_store=links,
        keyword_index=kw,
        settings=settings,
        ns_filter=ns_filter,
    )

    # Bootstrap BM25 from existing memories
    all_rows = memories.all_memory_rows(include_deleted=True)
    mems = [Memory(**dict(r)) for r in all_rows]
    kw.rebuild(mems)
    print(f"BM25 rebuilt with {len(mems)} memories")

    # Build SweepService — standalone, no MemoryService coupling
    suggestions = LinkSuggestionStore(db)
    sweeper = SweepService(
        memory_store=memories,
        link_store=links,
        suggestion_store=suggestions,
        link_candidate_generator=link_candidate_generator,
        settings=settings,
        metrics_store=metrics,
        conn=db.conn,
    )

    if args.dry_run:
        print("\nDry-run mode: scanning only, no writes.")
        active_rows = memories.all_memory_rows(include_deleted=False)
        active_ids = [r["id"] for r in active_rows]
        print(f"Active memories to scan: {len(active_ids)}")
        total_candidates = 0
        for mem_id in active_ids[:10]:  # sample first 10
            try:
                candidates = link_candidate_generator.generate(mem_id)
                total_candidates += len(candidates)
            except Exception as e:
                print(f"  {mem_id}: error - {e}")
        print(f"Total candidates (first 10 memories): {total_candidates}")
        print("Dry run complete.")
    else:
        stats = sweeper.run()
        print("\nSweep complete:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
