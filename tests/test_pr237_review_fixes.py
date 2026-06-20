"""Regression tests for PR #237 review fixes (LKPR-99).

Covers the issues found during review:
  1.  BLOCKER — scripts/sweep-links.py called non-existent svc.sweep_links()
  2.  MAJOR  — MemoryService had dead suggestions attribute + db param
  3.  MAJOR  — SweepService wired in server.py with its own store (not via MemoryService)
"""

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

# ── BLOCKER: scripts/sweep-links.py crash ──────────────────────────────────


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
    from lorekeeper.config import Settings
    from lorekeeper.services.keyword_index import KeywordIndex
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
            assert "suggestions = LinkSuggestionStore(db)" in body_text, (
                "server.py init_service must create LinkSuggestionStore "
                "independently for SweepService"
            )

            # Must wire SweepService with that store
            assert "suggestion_store=suggestions" in body_text, (
                "server.py must pass the LinkSuggestionStore to SweepService"
            )

            # Must NOT pass suggestions to MemoryService
            assert "MemoryService(" in body_text
            for line in source_lines[body_start:body_end]:
                if "MemoryService(" in line:
                    assert "suggestions" not in line, (
                        "MemoryService constructor call must not receive "
                        "the suggestions store"
                    )
            return

    pytest.fail("Could not find init_service function in server.py")
