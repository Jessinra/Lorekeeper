import json
import subprocess
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Union, get_args, get_origin

import structlog
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lorekeeper.models import Memory, RelationType
from lorekeeper.serializers import (
    serialize_memory,
    serialize_memory_link,
    serialize_reflection,
    serialize_search_result,
    serialize_session,
)
from lorekeeper.server import get_service, init_service

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
async def lifespan(app: FastAPI):
    global _APP_VERSION
    log.info("dashboard_startup")
    _APP_VERSION = _resolve_version()
    log.info("version_resolved", version=_APP_VERSION)
    init_service()
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


# ── Memories ──────────────────────────────────────────────────────────────────

@app.get("/api/memories")
def list_memories(include_deleted: bool = False) -> list[dict[str, Any]]:
    svc = get_service()
    rows = svc.memories.all_memory_rows(include_deleted=include_deleted)
    link_counts: dict[str, int] = {}
    for lnk in svc.links.all_links():
        link_counts[lnk.source_memory_id] = link_counts.get(lnk.source_memory_id, 0) + 1
        link_counts[lnk.target_memory_id] = link_counts.get(lnk.target_memory_id, 0) + 1
    result = []
    for r in rows:
        mem = serialize_memory(Memory(**r))
        mem["link_count"] = link_counts.get(r["id"], 0)
        result.append(mem)
    return result


@app.get("/api/memories/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    svc = get_service()
    row = svc.memories.get_memory_row(memory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    links = svc.links.links_for_memory(memory_id)
    return {
        "memory": serialize_memory(Memory(**dict(row))),
        "links": [serialize_memory_link(lnk) for lnk in links],
    }


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


@app.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, bool]:
    store = get_service().memories
    if store.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    fields = body.model_dump(exclude_none=True)
    if "soft_deleted" in fields:
        fields["soft_deleted"] = int(fields["soft_deleted"])
    store.update_memory_fields(memory_id, **fields)
    return {"ok": True}


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, bool]:
    store = get_service().memories
    if store.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete_memory_row(memory_id)
    return {"ok": True}


# ── Links ─────────────────────────────────────────────────────────────────────

class LinkCreate(BaseModel):
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    reason: str
    score: float = 1.0


@app.get("/api/links")
def list_all_links(include_deleted: bool = False) -> list[dict[str, Any]]:
    svc = get_service()
    links = svc.links.all_links()
    all_rows = svc.memories.all_memory_rows(include_deleted=True)
    title_map = {r["id"]: r["title"] for r in all_rows}
    deleted_ids = {r["id"] for r in all_rows if r["soft_deleted"]}
    if not include_deleted:
        links = [
            lnk for lnk in links
            if lnk.source_memory_id not in deleted_ids and lnk.target_memory_id not in deleted_ids
        ]
    return [
        {
            **serialize_memory_link(lnk),
            "source_title": title_map.get(lnk.source_memory_id, lnk.source_memory_id[:12] + "…"),
            "target_title": title_map.get(lnk.target_memory_id, lnk.target_memory_id[:12] + "…"),
        }
        for lnk in links
    ]


@app.post("/api/links", status_code=201)
def create_link(body: LinkCreate) -> dict[str, Any]:
    svc = get_service()
    if svc.memories.get_memory_row(body.source_memory_id) is None:
        raise HTTPException(status_code=404, detail="Source memory not found")
    if svc.memories.get_memory_row(body.target_memory_id) is None:
        raise HTTPException(status_code=404, detail="Target memory not found")
    link = svc.links.insert_link(
        source_memory_id=body.source_memory_id,
        target_memory_id=body.target_memory_id,
        relation_type=body.relation_type,
        reason=body.reason,
        score=body.score,
    )
    return serialize_memory_link(link)


@app.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict[str, bool]:
    store = get_service().links
    if store.get_link(link_id) is None:
        raise HTTPException(status_code=404, detail="Link not found")
    store.delete_link(link_id)
    return {"ok": True}


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_score: float = 0.1


# ── Config ────────────────────────────────────────────────────────────────────

_READONLY_KEYS = {"data_dir", "embedding_model"}


def _unwrap_optional(tp: Any) -> Any:
    """Unwrap Optional[T] / Union[T, None] to T."""
    origin = get_origin(tp)
    if origin is Union:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        return non_none[0] if len(non_none) == 1 else tp
    return tp


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    s = get_service().settings
    overridden_keys = set(get_service().config.get_overrides().keys())
    return {
        "data_dir":                        str(s.data_dir),
        "embedding_model":                 s.embedding_model,
        "duplicate_threshold":             s.duplicate_threshold,
        "w_semantic":                      s.w_semantic,
        "w_keyword":                       s.w_keyword,
        "w_memory":                        s.w_memory,
        "w_usage":                         s.w_usage,
        "score_bump_up":                   s.score_bump_up,
        "score_bump_down":                 s.score_bump_down,
        "score_min":                       s.score_min,
        "score_max":                       s.score_max,
        "soft_delete_confidence_threshold":s.soft_delete_confidence_threshold,
        "confidence_window_size":          s.confidence_window_size,
        "search_limit":                    s.search_limit,
        "max_links_per_memory":            s.max_links_per_memory,
        "usage_normalisation_cap":         s.usage_normalisation_cap,
        "decay_lambda":                    s.decay_lambda,
        "new_memory_default_score":        s.new_memory_default_score,
        "auto_link_enabled":               s.auto_link_enabled,
        "auto_link_k":                     s.auto_link_k,
        "auto_link_threshold":             s.auto_link_threshold,
        "_overridden_keys":                sorted(overridden_keys),
    }


class ConfigUpdate(BaseModel):
    duplicate_threshold: float | None = None
    w_semantic: float | None = None
    w_keyword: float | None = None
    w_memory: float | None = None
    w_usage: float | None = None
    score_bump_up: float | None = None
    score_bump_down: float | None = None
    score_min: float | None = None
    score_max: float | None = None
    soft_delete_confidence_threshold: int | None = None
    confidence_window_size: int | None = None
    search_limit: int | None = None
    max_links_per_memory: int | None = None
    usage_normalisation_cap: int | None = None
    decay_lambda: float | None = None
    new_memory_default_score: float | None = None
    auto_link_enabled: bool | None = None
    auto_link_k: int | None = None
    auto_link_threshold: float | None = None


@app.patch("/api/config")
def update_config(body: ConfigUpdate) -> dict[str, bool]:
    """Update config overrides with type validation.
    Read-only keys (data_dir, embedding_model) are silently skipped.
    Returns 422 with detail on type mismatch.
    """
    _TYPE_MAP = {k: _unwrap_optional(v.annotation) for k, v in ConfigUpdate.model_fields.items()}
    svc = get_service()
    s = svc.settings
    for key, value in body.model_dump(exclude_none=True).items():
        if key in _READONLY_KEYS:
            continue
        expected = _TYPE_MAP.get(key)
        if expected is not None and not isinstance(value, expected):
            raise HTTPException(
                status_code=422,
                detail=f"Config '{key}' expects {expected.__name__}, got {type(value).__name__}",
            )
        setattr(s, key, value)
        svc.config.set_override(key, value)
    return {"ok": True}


@app.get("/api/reflections")
def list_reflections() -> list[dict[str, Any]]:
    store = get_service().reflections
    return [serialize_reflection(dict(r)) for r in store.all_reflections()]


@app.get("/api/reflections/{reflection_id}")
def get_reflection_detail(reflection_id: str) -> dict[str, Any]:
    store = get_service().reflections
    row = store.get_reflection(reflection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    sessions = store.sessions_for_reflection(reflection_id)
    return {
        "reflection": serialize_reflection(dict(row)),
        "sessions": [serialize_session(dict(s)) for s in sessions],
    }


@app.get("/api/sessions")
def list_sessions(with_content: bool = True) -> list[dict[str, Any]]:
    store = get_service().reflections
    rows = store.sessions_with_content() if with_content else store.all_sessions()
    return [serialize_session(dict(s)) for s in rows]


@app.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict[str, Any]:
    store = get_service().reflections
    row = store.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    reflection = None
    if row["reflection_id"]:
        ref_row = store.get_reflection(row["reflection_id"])
        if ref_row:
            reflection = {
                "id": ref_row["id"],
                "created_at": ref_row["created_at"],
                "summary": ref_row["summary"],
            }
    return {"session": serialize_session(dict(row)), "reflection": reflection}


@app.post("/api/search")
def search(body: SearchRequest) -> list[dict[str, Any]]:
    results = get_service().search(
        body.query, limit=body.limit, min_score=body.min_score, include_links=False
    )
    return [
        serialize_search_result(
            r,
            truncate_content=300,
            exclude_memory_fields={"created_at", "updated_at", "confidence", "confidence_count"},
            exclude_relevance_fields={"decay_factor"},
            round_relevance=4,
            include_links=False,
        )
        for r in results
    ]


# ── Backup: Export / Import ───────────────────────────────────────────────────

@app.get("/api/export")
def export_dump(include_deleted: bool = False) -> Response:
    svc = get_service()
    now = datetime.now(UTC)
    memories = [
        serialize_memory(Memory(**dict(r)))
        for r in svc.memories.all_memory_rows(include_deleted=include_deleted)
    ]
    links = [serialize_memory_link(lnk) for lnk in svc.links.all_links()]
    payload = {
        "version": "2",
        "exported_at": now.isoformat(),
        "memories": memories,
        "links": links,
    }
    filename = f"lorekeeper-{now.strftime('%Y-%m-%d')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_dump(raw: bytes) -> tuple[list[Any], list[Any]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}") from e
    if not isinstance(data.get("memories"), list) or not isinstance(data.get("links"), list):
        raise HTTPException(status_code=422, detail='File must have "memories" and "links" arrays')
    return data["memories"], data["links"]


@app.post("/api/import/preview")
async def import_preview(file: UploadFile = File(...)) -> dict[str, Any]:
    memories, links = _parse_dump(await file.read())
    return get_service().import_dump(memories, links, dry_run=True)


@app.post("/api/import/confirm")
async def import_confirm(file: UploadFile = File(...)) -> dict[str, Any]:
    memories, links = _parse_dump(await file.read())
    return get_service().import_dump(memories, links, dry_run=False)


# ── Metrics ───────────────────────────────────────────────────────────────────

@app.get("/api/metrics")
def get_metrics(hours: int = 24) -> dict[str, Any]:
    """Return per-minute API call counts bucketed by tool, for the last `hours` hours."""
    store = get_service().metrics
    rows = store.get_metrics(hours=hours)
    # Build sorted list of unique buckets and tools
    buckets: list[str] = []
    tools: set[str] = set()
    data: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = row["minute_bucket"]
        tool   = row["tool_name"]
        count  = row["count"]
        tools.add(tool)
        if bucket not in data:
            data[bucket] = {}
            buckets.append(bucket)
        data[bucket][tool] = count
    return {
        "hours": hours,
        "buckets": buckets,
        "tools": sorted(tools),
        "data": data,
    }
