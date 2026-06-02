# LKPR-52 Lean Simplification Pass — Implementation Plan

> **For Hermes:** This plan is self-contained. Execute task-by-task. Do NOT add abstraction layers. Zero behavior change in happy path. Run tests after every phase.

**Goal:** Three zero-behavior-change mechanical refactors — transaction ownership, dashboard route split, schema extraction — each shrinking coupling and making the codebase easier to read and extend.

**Repo:** `/Users/jessinra/Code/lorekeeper`
**Branch:** `feature/LKPR-52-lean-simplification-pass`
**Test command:** `cd /Users/jessinra/Code/lorekeeper && uv run pytest`
**Lint command:** `uv run ruff check src tests`

---

## Phase 1: Transaction ownership → orchestrator

**Why:** 16 scattered `conn.commit()` calls across 6 store files means each write commits independently. The orchestrator can't batch a logical operation (insert memory + auto-link) into one transaction. Moving commit ownership to the orchestrator is the correct boundary.

**Scope:** Remove `self._conn.commit()` from all store methods. Add a single `self._db.conn.commit()` (or `conn.commit()`) call in `orchestrator.py` at the end of each logical operation.

**Files touched:**
- `src/lorekeeper/services/memory_store.py` — 4 commits at lines 62, 163, 176, 180
- `src/lorekeeper/services/link_store.py` — 3 commits at lines 77, 127, 139
- `src/lorekeeper/services/reflection_store.py` — 3 commits at lines 67, 103, 113
- `src/lorekeeper/services/config_store.py` — 2 commits (lines 43, 50)
- `src/lorekeeper/services/database.py` — 3 commits (lines 274, 310, 331) — **do NOT remove these** (they belong to Database lifecycle and migration logic)
- `src/lorekeeper/services/metrics_store.py` — 1 commit at line 28
- `src/lorekeeper/services/orchestrator.py` — add commits here

**Rules:**
- `database.py` PRAGMA commits and migration commits stay — those are lifecycle, not store writes
- `link_store.py`'s `insert_link` IntegrityError path does NOT commit (it's in error handling) — leave that alone
- Dashboard `app.py` routes call stores directly for some operations (e.g. `store.update_memory_fields`, `store.delete_memory_row`, `store.delete_link`) — these routes need explicit commits added after those calls (since stores lose their auto-commit)

---

### Task 1.1: Remove commits from MemoryStore

**Objective:** Strip all 4 `self._conn.commit()` from `memory_store.py`.

**File:** `src/lorekeeper/services/memory_store.py`

**Step 1: Remove commits**

Remove `self._conn.commit()` from:
- `upsert_memory_row` (line 62)
- `update_memory_fields` (line 163)
- `bulk_increment_usage_count` (line 176)
- `delete_memory_row` (line 180)

**Step 2: Verify lint passes**
```bash
cd /Users/jessinra/Code/lorekeeper && uv run ruff check src/lorekeeper/services/memory_store.py
```

**Step 3: Commit**
```bash
git add src/lorekeeper/services/memory_store.py
git commit -m "[LKPR-52] refactor: remove auto-commit from MemoryStore"
```

---

### Task 1.2: Remove commits from LinkStore

**Objective:** Strip 3 `self._conn.commit()` from `link_store.py`.

**File:** `src/lorekeeper/services/link_store.py`

**Step 1: Remove commits**

Remove `self._conn.commit()` from:
- `insert_link` happy path (after the INSERT, line 77) — **keep** the error handling path as-is (no commit there anyway)
- `update_link_fields` (line 127)
- `delete_link` (line 139)

**Step 2: Lint + commit**
```bash
uv run ruff check src/lorekeeper/services/link_store.py
git add src/lorekeeper/services/link_store.py
git commit -m "[LKPR-52] refactor: remove auto-commit from LinkStore"
```

---

### Task 1.3: Remove commits from ReflectionStore

**Objective:** Strip 3 `self._conn.commit()` from `reflection_store.py`.

**File:** `src/lorekeeper/services/reflection_store.py`

**Step 1:** Remove `self._conn.commit()` from `insert_reflection` and `upsert_session` (both write methods).

**Step 2: Lint + commit**
```bash
uv run ruff check src/lorekeeper/services/reflection_store.py
git add src/lorekeeper/services/reflection_store.py
git commit -m "[LKPR-52] refactor: remove auto-commit from ReflectionStore"
```

---

### Task 1.4: Remove commits from MetricsStore + ConfigStore

**Objective:** Strip commits from remaining 2 stores.

**Files:** `src/lorekeeper/services/metrics_store.py`, `src/lorekeeper/services/config_store.py`

**Step 1:** Remove `self._conn.commit()` from the write methods in each file.

**Step 2: Lint + commit**
```bash
uv run ruff check src/lorekeeper/services/metrics_store.py src/lorekeeper/services/config_store.py
git add src/lorekeeper/services/metrics_store.py src/lorekeeper/services/config_store.py
git commit -m "[LKPR-52] refactor: remove auto-commit from MetricsStore and ConfigStore"
```

---

### Task 1.5: Add commits to orchestrator at operation boundaries

**Objective:** Each logical public method in `orchestrator.py` commits after it finishes its writes.

**File:** `src/lorekeeper/services/orchestrator.py`

**Step 1: Add a commit helper**

At the top of `MemoryService`, add:
```python
def _commit(self) -> None:
    """Commit the shared SQLite connection. Called after each logical operation."""
    self.memories._conn.commit()
```

**Step 2: Add `self._commit()` at the end of each write method:**

- `insert()` — after the KW rebuild block (end of method, before `return`)
- `remember()` — after `_rebuild_kw()` and `_auto_link()` (end of method, before `return`)
- `update()` — end of method, before `return`
- `submit_reflection()` — after the auto-insert block, before `return`
- `import_dump()` — end of method, before `return`

**Note on search:** `search()` and `search_by_ids()` call `update_memory_fields` and `bulk_increment_usage_count`. These are fire-and-forget usage counters. Add `self._commit()` at the end of both search methods.

**Step 3: Add commits to dashboard routes that write directly to stores**

In `src/lorekeeper/dashboard/app.py`, the following routes call store methods directly (bypassing orchestrator):
- `update_memory` → `store.update_memory_fields(...)` → add `svc.memories._conn.commit()` after
- `delete_memory` → `store.delete_memory_row(...)` → add `svc.memories._conn.commit()` after  
- `create_link` → `svc.links.insert_link(...)` → add `svc.links._conn.commit()` after
- `delete_link` → `store.delete_link(...)` → add `svc.links._conn.commit()` after
- `update_config` → `svc.config.set_override(...)` → add `svc.config._conn.commit()` after the loop

**Step 4: Run tests**
```bash
cd /Users/jessinra/Code/lorekeeper && uv run pytest
```
Expected: all green.

**Step 5: Lint + commit**
```bash
uv run ruff check src/
git add src/lorekeeper/services/orchestrator.py src/lorekeeper/dashboard/app.py
git commit -m "[LKPR-52] refactor: centralize commit ownership in orchestrator"
```

---

## Phase 2: Dashboard route split

**Why:** `app.py` is 423 lines mixing FastAPI setup, Pydantic schemas, and route handlers for 7 domains. Each domain file is independently readable and testable. The mount + lifespan stay in `app.py` (≤80 lines after split).

**Target file structure:**
```
src/lorekeeper/dashboard/
  app.py          # FastAPI init, mounts, lifespan only (≤80 lines)
  schemas.py      # All Pydantic request/response models
  routes/
    __init__.py
    memories.py   # GET/PATCH/DELETE /api/memories
    links.py      # GET/POST/DELETE /api/links
    search.py     # POST /api/search
    config.py     # GET/PATCH /api/config
    reflections.py # GET /api/reflections + /api/sessions
    backup.py     # GET /api/export, POST /api/import/*
    metrics.py    # GET /api/metrics
```

---

### Task 2.1: Create `dashboard/schemas.py`

**Objective:** Extract all Pydantic models from `app.py` into a shared schemas module.

**Create:** `src/lorekeeper/dashboard/schemas.py`

```python
"""Pydantic request/response schemas for the Lorekeeper dashboard API."""
from __future__ import annotations
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from lorekeeper.models import RelationType


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


class LinkCreate(BaseModel):
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    reason: str
    score: float = 1.0


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_score: float = 0.1


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


_READONLY_KEYS = {"data_dir", "embedding_model"}


def unwrap_optional(tp: Any) -> Any:
    """Unwrap Optional[T] / Union[T, None] to T."""
    origin = get_origin(tp)
    if origin is Union:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        return non_none[0] if len(non_none) == 1 else tp
    return tp
```

**Step 2: Lint + commit**
```bash
uv run ruff check src/lorekeeper/dashboard/schemas.py
git add src/lorekeeper/dashboard/schemas.py
git commit -m "[LKPR-52] refactor: extract dashboard Pydantic schemas to schemas.py"
```

---

### Task 2.2: Create `routes/` package and route files

**Objective:** One file per domain with `APIRouter`.

**Create:** `src/lorekeeper/dashboard/routes/__init__.py` (empty)

**Create:** `src/lorekeeper/dashboard/routes/memories.py`
```python
"""Memory CRUD routes."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.models import Memory
from lorekeeper.serializers import serialize_memory, serialize_memory_link
from lorekeeper.server import get_service
from lorekeeper.dashboard.schemas import MemoryUpdate

router = APIRouter()


@router.get("/api/memories")
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


@router.get("/api/memories/{memory_id}")
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


@router.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, bool]:
    svc = get_service()
    store = svc.memories
    if store.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    fields = body.model_dump(exclude_none=True)
    if "soft_deleted" in fields:
        fields["soft_deleted"] = int(fields["soft_deleted"])
    store.update_memory_fields(memory_id, **fields)
    svc.memories._conn.commit()
    return {"ok": True}


@router.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, bool]:
    svc = get_service()
    store = svc.memories
    if store.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete_memory_row(memory_id)
    svc.memories._conn.commit()
    return {"ok": True}
```

**Create:** `src/lorekeeper/dashboard/routes/links.py`
```python
"""Link CRUD routes."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.serializers import serialize_memory_link
from lorekeeper.server import get_service
from lorekeeper.dashboard.schemas import LinkCreate

router = APIRouter()


@router.get("/api/links")
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


@router.post("/api/links", status_code=201)
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
    svc.links._conn.commit()
    return serialize_memory_link(link)


@router.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict[str, bool]:
    svc = get_service()
    store = svc.links
    if store.get_link(link_id) is None:
        raise HTTPException(status_code=404, detail="Link not found")
    store.delete_link(link_id)
    svc.links._conn.commit()
    return {"ok": True}
```

**Create:** `src/lorekeeper/dashboard/routes/search.py`
```python
"""Search route."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter

from lorekeeper.serializers import serialize_search_result
from lorekeeper.server import get_service
from lorekeeper.dashboard.schemas import SearchRequest

router = APIRouter()


@router.post("/api/search")
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
```

**Create:** `src/lorekeeper/dashboard/routes/config.py`
```python
"""Config read/write routes."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.server import get_service
from lorekeeper.dashboard.schemas import ConfigUpdate, _READONLY_KEYS, unwrap_optional

router = APIRouter()


@router.get("/api/config")
def get_config() -> dict[str, Any]:
    s = get_service().settings
    overridden_keys = set(get_service().config.get_overrides().keys())
    return {
        "data_dir":                         str(s.data_dir),
        "embedding_model":                  s.embedding_model,
        "duplicate_threshold":              s.duplicate_threshold,
        "w_semantic":                       s.w_semantic,
        "w_keyword":                        s.w_keyword,
        "w_memory":                         s.w_memory,
        "w_usage":                          s.w_usage,
        "score_bump_up":                    s.score_bump_up,
        "score_bump_down":                  s.score_bump_down,
        "score_min":                        s.score_min,
        "score_max":                        s.score_max,
        "soft_delete_confidence_threshold": s.soft_delete_confidence_threshold,
        "confidence_window_size":           s.confidence_window_size,
        "search_limit":                     s.search_limit,
        "max_links_per_memory":             s.max_links_per_memory,
        "usage_normalisation_cap":          s.usage_normalisation_cap,
        "decay_lambda":                     s.decay_lambda,
        "new_memory_default_score":         s.new_memory_default_score,
        "auto_link_enabled":                s.auto_link_enabled,
        "auto_link_k":                      s.auto_link_k,
        "auto_link_threshold":              s.auto_link_threshold,
        "_overridden_keys":                 sorted(overridden_keys),
    }


@router.patch("/api/config")
def update_config(body: ConfigUpdate) -> dict[str, bool]:
    _TYPE_MAP = {k: unwrap_optional(v.annotation) for k, v in ConfigUpdate.model_fields.items()}
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
    svc.config._conn.commit()
    return {"ok": True}
```

**Create:** `src/lorekeeper/dashboard/routes/reflections.py`
```python
"""Reflections and sessions read routes."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.serializers import serialize_reflection, serialize_session
from lorekeeper.server import get_service

router = APIRouter()


@router.get("/api/reflections")
def list_reflections() -> list[dict[str, Any]]:
    store = get_service().reflections
    return [serialize_reflection(dict(r)) for r in store.all_reflections()]


@router.get("/api/reflections/{reflection_id}")
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


@router.get("/api/sessions")
def list_sessions(with_content: bool = True) -> list[dict[str, Any]]:
    store = get_service().reflections
    rows = store.sessions_with_content() if with_content else store.all_sessions()
    return [serialize_session(dict(s)) for s in rows]


@router.get("/api/sessions/{session_id}")
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
```

**Create:** `src/lorekeeper/dashboard/routes/backup.py`
```python
"""Export and import routes."""
from __future__ import annotations
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from lorekeeper.models import Memory
from lorekeeper.serializers import serialize_memory, serialize_memory_link
from lorekeeper.server import get_service

router = APIRouter()


def _parse_dump(raw: bytes) -> tuple[list[Any], list[Any]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}") from e
    if not isinstance(data.get("memories"), list) or not isinstance(data.get("links"), list):
        raise HTTPException(status_code=422, detail='File must have "memories" and "links" arrays')
    return data["memories"], data["links"]


@router.get("/api/export")
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


@router.post("/api/import/preview")
async def import_preview(file: UploadFile = File(...)) -> dict[str, Any]:
    memories, links = _parse_dump(await file.read())
    return get_service().import_dump(memories, links, dry_run=True)


@router.post("/api/import/confirm")
async def import_confirm(file: UploadFile = File(...)) -> dict[str, Any]:
    memories, links = _parse_dump(await file.read())
    return get_service().import_dump(memories, links, dry_run=False)
```

**Create:** `src/lorekeeper/dashboard/routes/metrics.py`
```python
"""Metrics route."""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter

from lorekeeper.server import get_service

router = APIRouter()


@router.get("/api/metrics")
def get_metrics(hours: int = 24) -> dict[str, Any]:
    store = get_service().metrics
    rows = store.get_metrics(hours=hours)
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
```

**Step 2: Lint all new files**
```bash
uv run ruff check src/lorekeeper/dashboard/routes/ src/lorekeeper/dashboard/schemas.py
```

**Step 3: Commit**
```bash
git add src/lorekeeper/dashboard/routes/ src/lorekeeper/dashboard/schemas.py
git commit -m "[LKPR-52] refactor: split dashboard routes into per-domain modules"
```

---

### Task 2.3: Rewrite `app.py` to include routers

**Objective:** Strip `app.py` down to FastAPI init + mounts + router includes. Target ≤80 lines.

**Rewrite** `src/lorekeeper/dashboard/app.py`:
```python
"""Lorekeeper Dashboard — FastAPI application entry point."""
from __future__ import annotations

import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from lorekeeper.server import init_service
from lorekeeper.dashboard.routes import memories, links, search, config, reflections, backup, metrics

log = structlog.get_logger()
STATIC_DIR = Path(__file__).parent / "static"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

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

app.mount("/css", StaticFiles(directory=STATIC_DIR / "css"), name="css")
app.mount("/js",  StaticFiles(directory=STATIC_DIR / "js"),  name="js")


@app.get("/", include_in_schema=False)
def index() -> Response:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return Response(
        content=html.replace("{%VERSION%}", _APP_VERSION),
        media_type="text/html",
    )


# Register domain routers
for _router in [memories.router, links.router, search.router, config.router,
                reflections.router, backup.router, metrics.router]:
    app.include_router(_router)
```

**Step 2: Run tests**
```bash
cd /Users/jessinra/Code/lorekeeper && uv run pytest
```

**Step 3: Lint + commit**
```bash
uv run ruff check src/lorekeeper/dashboard/app.py
git add src/lorekeeper/dashboard/app.py
git commit -m "[LKPR-52] refactor: slim app.py to init+mounts only, include domain routers"
```

---

## Phase 3: Cleanup pass

### Task 3.1: Run full lint + test suite

```bash
cd /Users/jessinra/Code/lorekeeper && uv run ruff check src tests && uv run pytest
```

Expected: green. Fix any lint errors before proceeding.

### Task 3.2: Final commit + PR

```bash
git push origin feature/LKPR-52-lean-simplification-pass
```

Then tell Jason: "LKPR-52 ready for review — branch `feature/LKPR-52-lean-simplification-pass`"

---

## Verification Checklist

- [ ] `uv run pytest` passes (all green)
- [ ] `uv run ruff check src tests` clean
- [ ] `app.py` ≤ 80 lines
- [ ] No `conn.commit()` in store methods (except `database.py` lifecycle commits)
- [ ] Each route file ≤ 60 lines
- [ ] Zero new classes introduced
- [ ] Zero API behavior change
