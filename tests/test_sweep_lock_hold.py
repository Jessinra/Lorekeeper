"""Regression tests: SQLite writer-lock hold time during sweep + busy_timeout.

Verifies the fix that the sweep acquires the writer lock ONLY for the final
write burst (Phase 2), not across the slow generate() compute (Phase 1), and
that Database sets busy_timeout so concurrent writers wait instead of crashing.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from lorekeeper.config import Settings
from lorekeeper.services.database import Database
from lorekeeper.services.sweep_service import SweepService
from tests._helpers import build_stores


class _Candidate:
    """Minimal stand-in for a LinkCandidateGenerator result."""

    def __init__(self, src: str, tgt: str, score: float = 0.9) -> None:
        self.source_lore_id = src
        self.target_lore_id = tgt
        self.weighted_score = score
        self.cosine_score = score
        self.bm25_score = 0.0
        self.entity_score = 0.0
        self.temporal_score = 0.0


def _insert_memory(stores, lore_id: str, title: str) -> None:
    now = "2026-06-21T00:00:00+00:00"
    stores.memories.upsert_memory_row(
        id=lore_id,
        title=title,
        description=title,
        content=title,
        created_at=now,
        updated_at=now,
        score=5.0,
        source_type="observed",
    )


def test_database_sets_busy_timeout(tmp_path: Path) -> None:
    """Database must set busy_timeout (default 5000ms, configurable)."""
    db = Database(tmp_path / "default.db")
    assert db.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000

    db2 = Database(tmp_path / "custom.db", busy_timeout_ms=1234)
    assert db2.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 1234


def test_sweep_no_write_lock_during_generate(tmp_path: Path) -> None:
    """The sweep must NOT hold the writer lock while generate() runs.

    A second connection with busy_timeout=0 attempts BEGIN IMMEDIATE (acquire
    writer lock) from inside the generator. If the sweep held the writer lock
    during compute, this would raise 'database is locked'. It must succeed,
    proving the lock is free during Phase 1.
    """
    db_path = tmp_path / "lore.db"
    stores = build_stores(db_path)
    for i in range(3):
        _insert_memory(stores, f"m{i}", f"memory {i}")
    stores.db.conn.commit()

    probe = sqlite3.connect(str(db_path), timeout=0)
    probe.execute("PRAGMA busy_timeout = 0")

    lock_was_free = {"ok": False, "checked": False}

    class _Generator:
        def generate(self, mem_id: str):
            # Called during Phase 1 — the writer lock must be free here.
            if not lock_was_free["checked"]:
                lock_was_free["checked"] = True
                try:
                    probe.execute("BEGIN IMMEDIATE")
                    probe.rollback()
                    lock_was_free["ok"] = True
                except sqlite3.OperationalError:
                    lock_was_free["ok"] = False
            return []

    sweep = SweepService(
        memory_store=stores.memories,
        link_store=stores.links,
        suggestion_store=stores.suggestions,
        link_candidate_generator=_Generator(),
        settings=Settings(),
        metrics_store=stores.metrics,
        conn=stores.db.conn,
    )
    sweep.run()
    probe.close()

    assert lock_was_free["checked"], "generator was never called"
    assert lock_was_free["ok"], (
        "writer lock was held during generate() — Phase 1 must not hold it"
    )


def test_sweep_still_writes_suggestions(tmp_path: Path) -> None:
    """Behaviour preserved: collected candidates are persisted in Phase 2."""
    db_path = tmp_path / "lore.db"
    stores = build_stores(db_path)
    _insert_memory(stores, "a", "alpha")
    _insert_memory(stores, "b", "beta")
    stores.db.conn.commit()

    class _Generator:
        def __init__(self) -> None:
            self._done = False

        def generate(self, mem_id: str):
            # Emit one candidate on the first call only (avoid duplicates).
            if self._done:
                return []
            self._done = True
            return [_Candidate("a", "b", score=0.95)]

    sweep = SweepService(
        memory_store=stores.memories,
        link_store=stores.links,
        suggestion_store=stores.suggestions,
        link_candidate_generator=_Generator(),
        settings=Settings(),
        metrics_store=stores.metrics,
        conn=stores.db.conn,
    )
    stats = sweep.run()

    assert stats["candidates_generated"] == 1
    pending = stores.suggestions.get_pending_suggestions()
    assert len(pending) == 1
    assert {pending[0].source_memory_id, pending[0].target_memory_id} == {"a", "b"}
