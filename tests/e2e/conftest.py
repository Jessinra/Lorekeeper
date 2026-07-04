"""E2E dashboard test infrastructure — isolated uvicorn server with seeded data."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import requests

# ---------------------------------------------------------------------------
# Session-scoped fixtures: seed DB, start uvicorn, provide base_url
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Isolated temp LORE_DATA_DIR so E2E tests never touch real data."""
    return tmp_path_factory.mktemp("lorekeeper-e2e")


def _unset_env(key: str) -> str | None:
    """Pop an env var, return its old value (or None)."""
    return os.environ.pop(key, None)


def _restore_env(key: str, old: str | None) -> None:
    """Restore or delete an env var."""
    if old is not None:
        os.environ[key] = old
    else:
        os.environ.pop(key, None)


@pytest.fixture(scope="session")
def seed_db(e2e_data_dir: Path) -> None:
    """Initialise the SQLite + LanceDB store and insert seed memories.

    Runs once per session so all E2E tests share the same seeded state.
    """
    _old_lore = _unset_env("LORE_DATA_DIR")
    os.environ["LORE_DATA_DIR"] = str(e2e_data_dir)

    try:
        from lorekeeper.server import get_memory_processor, init_service

        init_service()
        proc = get_memory_processor()

        proc.insert(
            [
                {"title": "Test Memory One", "content": "Python dev patterns", "score": 9.0},
                {"title": "Test Memory Two", "content": "Docker deployment guide", "score": 7.5},
                {"title": "Alpha Project Config", "content": "PostgreSQL config", "score": 8.0},
                {"title": "Beta Deployment Setup", "content": "K8s Helm setup", "score": 6.5},
                {"title": "Search Query Example", "content": "Search term docs", "score": 5.0},
                # Canary used exclusively by TestDelete — other tests must not depend on it
                {"title": "CANARY Delete Test", "content": "Canary for delete test", "score": 1.0},
            ],
            links=[],
        )

        # Reset singleton so the dashboard's lifespan re-initialises from disk
        import lorekeeper.server as srv_mod

        srv_mod._memory_store = None
        srv_mod._link_store = None
        srv_mod._db = None
        srv_mod._suggestion_processor = None
        srv_mod._memory_processor = None
        srv_mod._reflection_processor = None
        srv_mod._link_processor = None
        srv_mod._admin_processor = None
    finally:
        _restore_env("LORE_DATA_DIR", _old_lore)


@pytest.fixture(scope="session")
def live_server(e2e_data_dir: Path, seed_db: None) -> Generator[str]:
    """Start uvicorn on a random port pointing at the seeded data dir.

    Yields the ``http://127.0.0.1:<port>`` URL.
    """
    env = os.environ.copy()
    env["LORE_DATA_DIR"] = str(e2e_data_dir)
    env["LORE_DASH_RELOAD"] = "0"

    # Find a free ephemeral port
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Write stderr to a temp file so we can show it on failure without
    # risking deadlock from filling the pipe buffer (uvicorn access logs +
    # Playwright asset requests can generate substantial output).
    stderr_log = e2e_data_dir / "uvicorn-stderr.log"

    with stderr_log.open("wb") as stderr_fh:
        proc = subprocess.Popen(
            [
                "uv", "run", "--extra", "dashboard",
                "uvicorn", "lorekeeper.dashboard.app:app",
                "--host", "127.0.0.1",
                "--port", str(port),
            ],
            cwd=repo_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=stderr_fh,
        )

        url = f"http://127.0.0.1:{port}"

        # Wait for the server to accept requests (up to 30 s)
        deadline = time.monotonic() + 30
        server_ok = False
        while time.monotonic() < deadline:
            # If process died before serving, bail early
            if proc.poll() is not None:
                break
            try:
                resp = requests.get(f"{url}/", timeout=2)
                if resp.status_code == 200:
                    server_ok = True
                    break
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(0.5)

        if not server_ok:
            # Extra attempt: maybe the server just started after the loop
            if proc.poll() is None:
                try:
                    resp = requests.get(f"{url}/", timeout=2)
                    server_ok = resp.status_code == 200
                except (requests.ConnectionError, requests.Timeout):
                    pass

        if not server_ok:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            err_text = stderr_log.read_text(errors="replace") if stderr_log.exists() else ""
            pytest.fail(
                f"Dashboard server did not start within 30 s at {url}\n"
                f"stderr:\n{err_text[:2000]}"
            )

        yield url

    # Teardown (outside the with block so the file handle is flushed/closed)
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def base_url(live_server: str) -> Generator[str, None, None]:
    """Provide base_url for pytest-playwright's ``page.goto``."""
    yield live_server


# ---------------------------------------------------------------------------
# Scope marker — tests in this directory use the ``e2e`` mark
# ---------------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-apply the ``e2e`` marker to all tests under tests/e2e/.

    ``tryfirst=True`` ensures markers are applied before pytest's own
    ``-m`` deselection hook runs, so ``addopts = "-m 'not e2e'"`` correctly
    excludes these tests from the default unit run.
    """
    for item in items:
        if item.nodeid.startswith("tests/e2e/"):
            item.add_marker(pytest.mark.e2e)
