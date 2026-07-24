#!/usr/bin/env python
"""Seed deterministic fixture data for the Dashboard V2 Playwright E2E suite.

Run from the repo root (the Playwright ``webServer`` command does this):

    uv run --extra dashboard python src/dashboard_v2/tests/seed.py

Seeds, in-process, BEFORE the FastAPI backend starts — mirroring the proven
``tests/e2e/conftest.py`` seed-then-serve pattern. This ordering matters:
the dashboard builds its in-memory BM25 index at startup, so the data must
already be on disk when uvicorn boots. Seeding via Playwright's ``globalSetup``
would run *after* the web server starts, leaving search stale.

Fixture shape:
  * 10 memories  → Home stat tiles > 0, Memories table rows, Query results
  * auto-linked  → Links table renders (insert auto-links similar memories)
  * 3 reflections → Sessions timeline renders
  * suggestion sweep → Review page pending candidates render

All writes go through the real composition root (``init_service`` + processors),
so this exercises the same code paths as production — no bespoke DB fiddling.
"""

from __future__ import annotations

import os
import shutil
import sys

# The dashboard package lives under src/; ensure it's importable when this
# script is invoked from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

# Keep tokenizers quiet and single-threaded in CI.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("LORE_DATA_DIR", "/tmp/lk-e2e")


def _reset_data_dir() -> None:
    """Wipe the seed data dir so every run starts from a clean, deterministic state.

    Without this the seed is non-idempotent: the fixture memories use
    near-identical text, so a second run against a populated dir trips the
    duplicate threshold (0.6·semantic + 0.4·keyword >= 0.85), ``insert`` returns
    0 inserted, and the ``< 10`` guard aborts the whole webServer boot. A fixture
    seed owns its data dir, so resetting it up front is correct and keeps local
    re-runs and CI identical.
    """
    data_dir = os.environ["LORE_DATA_DIR"]
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)


def main() -> None:
    _reset_data_dir()

    from lorekeeper.domains.memory.models import row_to_memory
    from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
    from lorekeeper.domains.suggestion.sweep import SweepService
    from lorekeeper.infra.keyword_index import KeywordIndex
    from lorekeeper.infra.search_engine import LanceDBEngine
    from lorekeeper.platform.metrics.repository import MetricsStore
    from lorekeeper.server import (
        get_db,
        get_link_store,
        get_memory_processor,
        get_memory_store,
        get_reflection_processor,
        get_settings,
        init_service,
    )

    # ── Composition root — builds stores, services, processors from LORE_DATA_DIR ──
    init_service()

    settings = get_settings()
    db = get_db()
    memory_store = get_memory_store()
    link_store = get_link_store()

    # ── 1. Memories (10) ──────────────────────────────────────────────────────
    # Near-identical text so (a) auto-link creates real links for the Links page
    # and (b) enough similar pairs remain for the sweep to surface suggestions.
    memory_processor = get_memory_processor()
    memories = [
        {
            "title": f"Fixture Memory {i}",
            "content": (
                f"Fixture memory {i}: testing dashboard interaction with real "
                "seeded backend data across memories, links and search."
            ),
            "source_type": "inferred" if i % 3 == 0 else "observed",
            "score": 5.0 + (i % 5),
        }
        for i in range(1, 11)
    ]
    result = memory_processor.insert(memories=memories, links=[])
    inserted = result.get("inserted_memories", [])
    if len(inserted) < 10:
        raise SystemExit(
            f"Seed failed: expected 10 memories inserted, got {len(inserted)}. "
            f"errors={result.get('errors')}"
        )

    # ── 2. Explicit links (deterministic relation types for the Links page) ────
    ids = [m["id"] for m in inserted]
    explicit_links = [
        {
            "source_memory_id": ids[0],
            "target_memory_id": ids[1],
            "relation_type": "related",
            "reason": "fixture: related pair",
        },
        {
            "source_memory_id": ids[2],
            "target_memory_id": ids[3],
            "relation_type": "supports",
            "reason": "fixture: supporting pair",
        },
    ]
    # insert with no new memories just creates the links (idempotent-ish; a
    # duplicate auto-link is reported as an error, not raised).
    memory_processor.insert(memories=[], links=explicit_links)

    # ── 3. Reflections (3) → Sessions timeline ─────────────────────────────────
    reflection_processor = get_reflection_processor()
    for i in range(1, 4):
        reflection_processor.submit_reflection(
            session_id=f"fixture-session-{i:03d}",
            summary=f"Fixture session {i}: explored memory retrieval patterns.",
            topic=f"topic-{i}",
            task_type="feature",
            lessons_learnt=[f"Lesson {i}a", f"Lesson {i}b"],
            factual_discoveries=[f"Discovery {i}"],
        )

    # ── 4. Suggestion sweep → Review page pending candidates ───────────────────
    # Wire a SweepService exactly as the composition root does (server.py), then
    # run one synchronous sweep. Populates the LinkSuggestionStore.
    engine = LanceDBEngine(settings.lancedb_path, settings.embedding_model)
    kw = KeywordIndex()
    kw.rebuild(
        [row_to_memory(r) for r in memory_store.all_memory_rows(include_deleted=True)]
    )
    ns_filter = None if settings.namespace == "shared" else [settings.namespace, "shared"]
    suggestion_store = LinkSuggestionStore(db)
    metrics_store = MetricsStore(db)
    generator = LinkCandidateGenerator(
        engine=engine,
        memory_store=memory_store,
        link_store=link_store,
        keyword_index=kw,
        settings=settings,
        ns_filter=ns_filter,
    )
    sweep = SweepService(
        memory_store=memory_store,
        link_store=link_store,
        suggestion_store=suggestion_store,
        link_candidate_generator=generator,
        settings=settings,
        metrics_store=metrics_store,
        conn=db.conn,
    )
    stats = sweep.run()

    print(
        "Seed complete: "
        f"{len(inserted)} memories, {len(explicit_links)} explicit links, "
        f"3 reflections, sweep candidates={stats.get('candidates_generated')}"
    )


if __name__ == "__main__":
    main()
