import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from lorekeeper.dashboard.routes import (
    backup,
    config,
    links,
    memories,
    metrics,
    query,
    reflections,
    search,
    suggestions,
)
from lorekeeper.server import init_service

log = structlog.get_logger()
STATIC_DIR = Path(__file__).parent / "static"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Computed once at startup — not on every request
_APP_VERSION: str = "unknown"


def _resolve_version() -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--tags"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        log.exception("version_resolve_failed")
        return "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _APP_VERSION
    log.info("dashboard_startup")
    _APP_VERSION = _resolve_version()
    log.info("version_resolved", version=_APP_VERSION)
    ctx = init_service()
    app.state.dashboard_handler = ctx.dashboard_handler
    log.info("dashboard_ready")
    yield


app = FastAPI(lifespan=lifespan, title="Lorekeeper Dashboard")

# Serve css/, js/ subdirectories as static assets
app.mount("/css", StaticFiles(directory=STATIC_DIR / "css"), name="css")
app.mount("/js",  StaticFiles(directory=STATIC_DIR / "js"),  name="js")


# ── Serve UI ──────────────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
def index() -> Response:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return Response(
        content=html.replace("{%VERSION%}", _APP_VERSION),
        media_type="text/html",
    )


# ── Route modules ─────────────────────────────────────────────────────────────

app.include_router(memories.router)
app.include_router(links.router)
app.include_router(search.router)
app.include_router(query.router)
app.include_router(config.router)
app.include_router(reflections.router)
app.include_router(backup.router)
app.include_router(metrics.router)
app.include_router(suggestions.router)
