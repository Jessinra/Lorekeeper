"""DashboardHandler — single struct for all dashboard route request/response formatting.

Thin shim between FastAPI routes and processors.
Only handles serialization — no validation, no metrics, no commit boundaries.
Those belong in the processor layer.

The dashboard lifespan stores one instance in ``app.state.dashboard_handler``.
Routes access it via ``request.app.state.dashboard_handler`` instead of
importing module-level getters from ``server.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.domains.memory.models import Memory
from lorekeeper.shared.serializers import (
    serialize_memory,
    serialize_memory_link,
    serialize_reflection,
    serialize_search_result,
    serialize_session,
)

if TYPE_CHECKING:
    from lorekeeper.domains.link.repository import LinkStore
    from lorekeeper.domains.memory.repository import MemoryStore
    from lorekeeper.infra.settings import Settings
    from lorekeeper.processors.admin import AdminProcessor
    from lorekeeper.processors.link import LinkProcessor
    from lorekeeper.processors.memory import MemoryProcessor
    from lorekeeper.processors.reflection import ReflectionProcessor
    from lorekeeper.processors.suggestion import SuggestionProcessor


class DashboardHandler:
    """Single handler struct owning all processors + stores for dashboard dispatch.

    Each method is a thin pass-through that formats request/response.
    Validation, metrics, and commit boundaries are owned by the processor layer.
    """

    def __init__(
        self,
        memory_processor: MemoryProcessor,
        suggestion_processor: SuggestionProcessor,
        reflection_processor: ReflectionProcessor,
        link_processor: LinkProcessor,
        admin_processor: AdminProcessor,
        memory_store: MemoryStore,
        link_store: LinkStore,
        settings: Settings,
    ) -> None:
        self._memp = memory_processor
        self._sugp = suggestion_processor
        self._refp = reflection_processor
        self._lnkp = link_processor
        self._admp = admin_processor
        self._memory_store = memory_store
        self._link_store = link_store
        self._settings = settings

    # ── Memories ─────────────────────────────────────────────────────────────

    @staticmethod
    def _pagination_response(
        items: list[dict[str, Any]],
        total: int,
        page: int,
        per_page: int,
        items_key: str = "memories",
    ) -> dict[str, Any]:
        """Build standard paginated response dict — reusable across handlers."""
        return {
            items_key: items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page)),
        }

    def list_memories(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        rows = self._memory_store.all_memory_rows(include_deleted=include_deleted)
        links = self._link_store.all_links()
        link_counts: dict[str, int] = {}
        for lnk in links:
            link_counts[lnk.source_memory_id] = link_counts.get(lnk.source_memory_id, 0) + 1
            link_counts[lnk.target_memory_id] = link_counts.get(lnk.target_memory_id, 0) + 1
        result = []
        for r in rows:
            mem = serialize_memory(Memory(**r))
            mem["link_count"] = link_counts.get(r["id"], 0)
            result.append(mem)
        return result

    def list_memories_paginated(
        self,
        page: int = 1,
        per_page: int = 50,
        query: str = "",
        namespace: str | None = None,
        include_deleted: bool = False,
        filter_preset: str | None = None,
        sort: str = "updated_at",
        sort_dir: str = "desc",
    ) -> dict[str, Any]:
        """Paginated, filtered memory listing with link counts."""
        rows, total = self._memory_store.search_memory_rows(
            page=page, per_page=per_page, query=query,
            namespace=namespace, include_deleted=include_deleted,
            filter_preset=filter_preset, sort=sort, sort_dir=sort_dir,
        )
        ids = [r["id"] for r in rows]
        link_counts = self._link_store.count_links_for_memories(ids)
        result = []
        for r in rows:
            mem = serialize_memory(Memory(**dict(r)))
            mem["links_count"] = link_counts.get(r["id"], 0)
            result.append(mem)
        return self._pagination_response(result, total, page, per_page)

    def get_memory_counts(self) -> dict[str, int]:
        return self._memory_store.get_counts_by_filter()

    def list_namespaces(self) -> list[str]:
        return self._memory_store.get_distinct_namespaces()

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        row = self._memory_store.get_memory_row(memory_id)
        if row is None:
            return None
        mem_links = self._link_store.links_for_memory(memory_id)
        return {
            "memory": serialize_memory(Memory(**dict(row))),
            "links": [serialize_memory_link(lnk) for lnk in mem_links],
        }

    def update_memory(self, memory_id: str, fields: dict[str, Any]) -> dict[str, bool]:
        return self._memp.update_memory_fields(memory_id, fields)

    def delete_memory(self, memory_id: str) -> dict[str, bool]:
        return self._memp.delete_memory(memory_id)

    # ── Links ────────────────────────────────────────────────────────────────

    def list_all_links(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        return self._lnkp.list_links(include_deleted=include_deleted)

    def create_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relation_type: str,
        reason: str,
        score: float = 1.0,
    ) -> dict[str, Any]:
        link = self._lnkp.create_link(
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relation_type=relation_type,
            reason=reason,
            score=score,
        )
        return serialize_memory_link(link)

    def delete_link(self, link_id: str) -> dict[str, bool]:
        self._lnkp.delete_link(link_id)
        return {"ok": True}

    # ── Search ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.1,
    ) -> list[dict[str, Any]]:
        results = self._memp.search(
            query, limit=limit, min_score=min_score, include_links=False,
        )
        return [
            serialize_search_result(
                r,
                truncate_content=300,
                exclude_memory_fields={
                    "created_at", "updated_at", "confidence", "confidence_count",
                },
                exclude_relevance_fields={"decay_factor"},
                round_relevance=4,
                include_links=False,
            )
            for r in results
        ]

    # ── Suggestions / Sweep ──────────────────────────────────────────────────

    def list_suggestions(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "weighted_score",
        sort_dir: str = "desc",
        memory_id: str | None = None,
    ) -> dict[str, Any]:
        page, total = self._sugp.list_pending(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir, memory_id=memory_id,
        )
        return {
            "items": [
                {
                    "id": r.id,
                    "source_memory_id": r.source_memory_id,
                    "source_title": r.source_title,
                    "target_memory_id": r.target_memory_id,
                    "target_title": r.target_title,
                    "weighted_score": r.weighted_score,
                    "cosine_score": r.cosine_score,
                    "bm25_score": r.bm25_score,
                    "entity_score": r.entity_score,
                    "temporal_score": r.temporal_score,
                    "confidence": r.confidence,
                    "created_at": r.created_at,
                }
                for r in page
            ],
            "total": total,
            "offset": offset,
        }

    def count_suggestions(self, memory_id: str | None = None) -> dict[str, int]:
        return {"count": self._sugp.count_pending(memory_id=memory_id)}

    def batch_suggestions(
        self,
        suggestion_ids: list[str],
        action: str,
    ) -> dict[str, Any]:
        result = self._sugp.review(suggestion_ids=suggestion_ids, action=action)
        return {
            "results": [
                {"id": r["id"], "status": r["status"], "message": r["message"]}
                for r in result.results
            ],
            "accepted": result.accepted,
            "rejected": result.rejected,
            "errors": [e["error"] for e in result.errors],
        }

    def trigger_sweep(self) -> dict[str, bool]:
        self._admp.trigger_sweep()
        return {"ok": True}

    def sweep_status(self) -> dict[str, str | None]:
        return self._admp.sweep_status()

    # ── Backup / Export ──────────────────────────────────────────────────────

    def export_dump(self, include_deleted: bool = False) -> dict[str, Any]:
        memories_list = [
            serialize_memory(Memory(**dict(r)))
            for r in self._memory_store.all_memory_rows(include_deleted=include_deleted)
        ]
        links_list = [serialize_memory_link(lnk) for lnk in self._link_store.all_links()]
        return {
            "memories": memories_list,
            "links": links_list,
        }

    def import_preview(
        self, memories_data: list[dict[str, Any]], links_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._memp.import_dump(memories_data, links_data, dry_run=True)

    def import_confirm(
        self, memories_data: list[dict[str, Any]], links_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._memp.import_dump(memories_data, links_data, dry_run=False)

    # ── Config ───────────────────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        return self._admp.get_config()

    def set_config(self, key: str, value: Any) -> None:
        self._admp.set_config(key, value)

    # ── Metrics ──────────────────────────────────────────────────────────────

    def get_metrics(self, hours: int = 24) -> dict[str, Any]:
        return self._admp.get_metrics(hours=hours)

    # ── Reflections / Sessions ───────────────────────────────────────────────

    def list_reflections(self) -> list[dict[str, Any]]:
        return [serialize_reflection(dict(r)) for r in self._refp.list_reflections()]

    def get_reflection_detail(self, reflection_id: str) -> dict[str, Any] | None:
        row = self._refp.get_reflection(reflection_id)
        if row is None:
            return None
        sessions = self._refp.sessions_for_reflection(reflection_id)
        return {
            "reflection": serialize_reflection(dict(row)),
            "sessions": [serialize_session(dict(s)) for s in sessions],
        }

    def list_sessions(self, with_content: bool = True) -> list[dict[str, Any]]:
        rows = self._refp.list_sessions(with_content=with_content)
        return [serialize_session(dict(s)) for s in rows]

    def get_session_detail(self, session_id: str) -> dict[str, Any] | None:
        row = self._refp.get_session(session_id)
        if row is None:
            return None
        reflection = None
        if row["reflection_id"]:
            ref_row = self._refp.get_reflection(row["reflection_id"])
            if ref_row:
                reflection = {
                    "id": ref_row["id"],
                    "created_at": ref_row["created_at"],
                    "summary": ref_row["summary"],
                }
        return {"session": serialize_session(dict(row)), "reflection": reflection}

    # ── Settings ─────────────────────────────────────────────────────────────

    @property
    def settings(self) -> Settings:
        return self._settings
