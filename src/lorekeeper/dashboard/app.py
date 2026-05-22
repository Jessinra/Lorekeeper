import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lorekeeper.models import RelationType
from lorekeeper.server import get_service, init_service

log = structlog.get_logger()
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    log.info("dashboard_startup")
    init_service()
    log.info("dashboard_ready")
    yield


app = FastAPI(lifespan=lifespan, title="Lorekeeper Dashboard")

# Serve css/, js/ subdirectories as static assets
app.mount("/css", StaticFiles(directory=STATIC_DIR / "css"), name="css")
app.mount("/js",  StaticFiles(directory=STATIC_DIR / "js"),  name="js")


# ── Serve UI ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# ── Memories ──────────────────────────────────────────────────────────────────

@app.get("/api/memories")
def list_memories(include_deleted: bool = False) -> list[dict[str, Any]]:
    store = get_service()._store
    rows = store.all_memory_rows(include_deleted=include_deleted)
    link_counts: dict[str, int] = {}
    for lnk in store.all_links():
        link_counts[lnk.source_memory_id] = link_counts.get(lnk.source_memory_id, 0) + 1
        link_counts[lnk.target_memory_id] = link_counts.get(lnk.target_memory_id, 0) + 1
    return [{**dict(r), "link_count": link_counts.get(r["id"], 0)} for r in rows]


@app.get("/api/memories/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    store = get_service()._store
    row = store.get_memory_row(memory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    links = store.links_for_memory(memory_id)
    return {
        "memory": dict(row),
        "links": [lnk.model_dump() for lnk in links],
    }


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


@app.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, bool]:
    store = get_service()._store
    if store.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    fields = body.model_dump(exclude_none=True)
    if "soft_deleted" in fields:
        fields["soft_deleted"] = int(fields["soft_deleted"])
    store.update_memory_fields(memory_id, **fields)
    return {"ok": True}


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, bool]:
    store = get_service()._store
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
    store = get_service()._store
    links = store.all_links()
    all_rows = store.all_memory_rows(include_deleted=True)
    title_map = {r["id"]: r["title"] for r in all_rows}
    deleted_ids = {r["id"] for r in all_rows if r["soft_deleted"]}
    if not include_deleted:
        links = [
            lnk for lnk in links
            if lnk.source_memory_id not in deleted_ids and lnk.target_memory_id not in deleted_ids
        ]
    return [
        {
            **lnk.model_dump(),
            "source_title": title_map.get(lnk.source_memory_id, lnk.source_memory_id[:12] + "…"),
            "target_title": title_map.get(lnk.target_memory_id, lnk.target_memory_id[:12] + "…"),
        }
        for lnk in links
    ]


@app.post("/api/links", status_code=201)
def create_link(body: LinkCreate) -> dict[str, Any]:
    store = get_service()._store
    if store.get_memory_row(body.source_memory_id) is None:
        raise HTTPException(status_code=404, detail="Source memory not found")
    if store.get_memory_row(body.target_memory_id) is None:
        raise HTTPException(status_code=404, detail="Target memory not found")
    link = store.insert_link(
        source_memory_id=body.source_memory_id,
        target_memory_id=body.target_memory_id,
        relation_type=body.relation_type,
        reason=body.reason,
        score=body.score,
    )
    return link.model_dump()


@app.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict[str, bool]:
    store = get_service()._store
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


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    s = get_service()._settings
    overridden_keys = set(get_service()._store.get_config_overrides().keys())
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


@app.patch("/api/config")
def update_config(body: ConfigUpdate) -> dict[str, bool]:
    s = get_service()._settings
    store = get_service()._store
    for key, value in body.model_dump(exclude_none=True).items():
        if key not in _READONLY_KEYS:
            setattr(s, key, value)
            store.set_config_override(key, value)
    return {"ok": True}


@app.get("/api/reflections")
def list_reflections() -> list[dict[str, Any]]:
    store = get_service()._store
    return [dict(r) for r in store.all_reflections()]


@app.get("/api/reflections/{reflection_id}")
def get_reflection_detail(reflection_id: str) -> dict[str, Any]:
    store = get_service()._store
    row = store.get_reflection(reflection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    sessions = store.sessions_for_reflection(reflection_id)
    return {
        "reflection": dict(row),
        "sessions": [dict(s) for s in sessions],
    }


@app.get("/api/sessions")
def list_sessions(with_content: bool = True) -> list[dict[str, Any]]:
    store = get_service()._store
    rows = store.sessions_with_content() if with_content else store.all_sessions()
    return [dict(s) for s in rows]


@app.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict[str, Any]:
    store = get_service()._store
    row = store.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    reflection = None
    if row["reflection_id"]:
        ref_row = store.get_reflection(row["reflection_id"])
        if ref_row:
            reflection = {"id": ref_row["id"], "created_at": ref_row["created_at"], "summary": ref_row["summary"]}
    return {"session": dict(row), "reflection": reflection}


@app.post("/api/search")
def search(body: SearchRequest) -> list[dict[str, Any]]:
    results = get_service().search(
        body.query, limit=body.limit, min_score=body.min_score, include_links=False
    )
    return [
        {
            "memory": {
                "id": r.memory.id,
                "title": r.memory.title,
                "description": r.memory.description,
                "content": r.memory.content[:300],
                "score": r.memory.score,
                "usage_count": r.memory.usage_count,
                "soft_deleted": r.memory.soft_deleted,
            },
            "relevance": {
                "combined_score": round(r.combined_score, 4),
                "semantic_score": round(r.semantic_score, 4),
                "keyword_score": round(r.keyword_score, 4),
            },
        }
        for r in results
    ]


# ── Backup: Export / Import ───────────────────────────────────────────────────

@app.get("/api/export")
def export_dump(include_deleted: bool = False) -> Response:
    store = get_service()._store
    now = datetime.now(timezone.utc)
    memories = [dict(r) for r in store.all_memory_rows(include_deleted=include_deleted)]
    for m in memories:
        m["soft_deleted"] = bool(m["soft_deleted"])
    links = [lnk.model_dump() for lnk in store.all_links()]
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
    store = get_service()._store
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
