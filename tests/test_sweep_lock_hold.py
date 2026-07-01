"""Regression tests: SQLite writer-lock hold time during sweep + busy_timeout.

Verifies the fix that the sweep acquires the writer lock ONLY for the final
write burst (Phase 2), not across the slow generate() compute (Phase 1), and
that Database sets busy_timeout so concurrent writers wait instead of crashing.
"""

from __future__ import annotations

import inspect
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from lorekeeper.domains.suggestion.sweep import SweepService
from lorekeeper.infra.database import Database
from lorekeeper.infra.settings import Settings
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


def test_sweep_links_script_dry_run(tmp_path):
    """scripts/sweep-links.py --dry-run must complete without error.

    Regression: PR #237 had svc.sweep_links() which didn't exist —
    the dry-run path must not crash.
    """
    script = Path(__file__).parent.parent / "scripts" / "sweep-links.py"
    assert script.exists(), f"Script not found: {script}"

    result = subprocess.run(
        [sys.executable, str(script), "--data-dir", str(tmp_path), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"sweep-links.py --dry-run failed (exit {result.returncode}):\n"
        f"  stdout: {result.stdout}\n"
        f"  stderr: {result.stderr}"
    )
    assert "Dry run complete" in result.stdout, (
        f"Expected 'Dry run complete' in output:\n{result.stdout}"
    )


# ── MAJOR: MemoryService layering invariants ────────────────────────────────


class FakeEngine:
    """Minimal stub (duplicates test_orchestrator.py) for building MemoryService
    without a real LanceDB engine."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def probe_score_scale(self) -> None:
        pass

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
        self._store[lore_id] = text
        return lore_id

    def search(self, query: str, limit: int = 200) -> list[dict]:
        return []

    def get_embeddings_batch(self, ids: list[str]) -> dict[str, list[float]]:
        return {}

    def get_all(self) -> list[dict]:
        return [{"lore_id": k, "mem0_id": k} for k in self._store]

    def normalize_score(self, raw: float) -> float:
        return raw

    def find_vector_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None


def test_memory_service_has_no_db_parameter():
    """MemoryService.__init__ must not accept a `db` parameter.

    Regression: PR #237 added `db: Database` solely for creating
    LinkSuggestionStore, which was dead code.
    """
    from lorekeeper.services.orchestrator import MemoryService

    sig = inspect.signature(MemoryService.__init__)
    params = list(sig.parameters.keys())

    assert "db" not in params, (
        f"MemoryService.__init__ must not accept 'db' parameter. "
        f"Parameters: {params}"
    )


def test_memory_service_has_no_suggestions_attr(tmp_path):
    """MemoryService instance must not expose a 'suggestions' attribute.

    Regression: PR #237 set self.suggestions = LinkSuggestionStore(db)
    on MemoryService, but no MemoryService method used it.
    """
    from lorekeeper.infra.keyword_index import KeywordIndex
    from lorekeeper.infra.settings import Settings
    from tests._helpers import build_service, build_stores

    engine = FakeEngine()
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()

    svc = build_service(stores, engine, kw, settings)

    assert not hasattr(svc, "suggestions"), (
        "MemoryService should not have a 'suggestions' attribute — "
        "LinkSuggestionStore belongs on SweepService, not the orchestrator."
    )


# ── MAJOR: SweepService isolation in server.py ──────────────────────────────


def test_sweep_service_created_separately_in_server():
    """server.py must create SweepService with its own LinkSuggestionStore,
    not via MemoryService.

    Regression: PR #237 originally had LinkSuggestionStore created inside
    MemoryService.__init__ — this test verifies the server wiring creates
    it independently.
    """
    import ast

    server_path = (
        Path(__file__).parent.parent / "src" / "lorekeeper" / "server.py"
    )
    tree = ast.parse(server_path.read_text())

    # Collect all top-level function bodies
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "init_service":
            source_lines = server_path.read_text().splitlines()
            body_start = node.lineno - 1  # 0-indexed
            body_end = node.end_lineno or len(source_lines)
            body_text = "\n".join(source_lines[body_start:body_end])

            # Must create a separate LinkSuggestionStore for SweepService
            assert "LinkSuggestionStore(sweep_db)" in body_text, (
                "server.py init_service must create LinkSuggestionStore "
                "independently for SweepService"
            )

            # Must wire SweepService with that store
            assert "suggestion_store=sweep_suggestions" in body_text, (
                "server.py must pass the LinkSuggestionStore to SweepService"
            )

            # Must NOT pass suggestions to MemoryService — use AST to check
            memory_calls = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "MemoryService"
            ]
            assert memory_calls, "Expected init_service to construct MemoryService"
            for call in memory_calls:
                assert all(kw.arg != "suggestions" for kw in call.keywords), (
                    "MemoryService constructor call must not receive "
                    "the suggestions store"
                )
            return

    pytest.fail("Could not find init_service function in server.py")
