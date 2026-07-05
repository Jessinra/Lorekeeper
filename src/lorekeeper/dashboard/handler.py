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
    Serialization helpers (``serialize_memory``, ``serialize_search_result``, etc.)
    live in ``shared/`` and are called here.
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

    def list_memories(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        return []  # TODO: MemoryStore.all_memory_rows + LinkStore.all_links → serialize

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        return None  # TODO: MemoryStore.get_memory_row + LinkStore.links_for_memory → serialize

    def update_memory(self, memory_id: str, fields: dict[str, Any]) -> dict[str, bool]:
        return {}  # TODO: MemoryProcessor.update_memory_fields

    def delete_memory(self, memory_id: str) -> dict[str, bool]:
        return {}  # TODO: MemoryProcessor.delete_memory

    # ── Links ────────────────────────────────────────────────────────────────

    def list_all_links(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        return []  # TODO: LinkProcessor.list_links

    def create_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relation_type: str,
        reason: str,
        score: float = 1.0,
    ) -> dict[str, Any]:
        return {}  # TODO: LinkProcessor.create_link → serialize

    def delete_link(self, link_id: str) -> dict[str, bool]:
        return {}  # TODO: LinkProcessor.delete_link

    # ── Search ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.1,
    ) -> list[dict[str, Any]]:
        return []  # TODO: MemoryProcessor.search → serialize with truncation

    # ── Suggestions / Sweep ──────────────────────────────────────────────────

    def list_suggestions(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "weighted_score",
        sort_dir: str = "desc",
        memory_id: str | None = None,
    ) -> dict[str, Any]:
        return {"items": [], "total": 0, "offset": offset}
        # TODO: SuggestionProcessor.list_pending → serialize

    def count_suggestions(self, memory_id: str | None = None) -> dict[str, int]:
        return {"count": 0}  # TODO: SuggestionProcessor.count_pending

    def batch_suggestions(
        self,
        suggestion_ids: list[str],
        action: str,
    ) -> dict[str, Any]:
        return {"results": [], "accepted": 0, "rejected": 0, "errors": []}
        # TODO: SuggestionProcessor.review

    def trigger_sweep(self) -> dict[str, bool]:
        return {"ok": True}  # TODO: AdminProcessor.trigger_sweep

    def sweep_status(self) -> dict[str, str | None]:
        return {"last_run_at": None, "next_run_at": None}  # TODO: AdminProcessor.sweep_status

    # ── Backup / Export ──────────────────────────────────────────────────────

    def export_dump(self, include_deleted: bool = False) -> dict[str, Any]:
        return {}  # TODO: MemoryStore + LinkStore → serialize → full payload

    def import_preview(
        self, memories_data: list[dict[str, Any]], links_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {}  # TODO: MemoryProcessor.import_dump(dry_run=True)

    def import_confirm(
        self, memories_data: list[dict[str, Any]], links_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {}  # TODO: MemoryProcessor.import_dump(dry_run=False)

    # ── Config ───────────────────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        return {}  # TODO: AdminProcessor.get_config

    def update_config(self, key: str, value: Any) -> None:
        return None  # TODO: AdminProcessor.set_config

    # ── Metrics ──────────────────────────────────────────────────────────────

    def get_metrics(self, hours: int = 24) -> dict[str, Any]:
        return {}  # TODO: AdminProcessor.get_metrics

    # ── Reflections / Sessions ───────────────────────────────────────────────

    def list_reflections(self) -> list[dict[str, Any]]:
        return []  # TODO: ReflectionProcessor.list_reflections → serialize

    def get_reflection_detail(self, reflection_id: str) -> dict[str, Any] | None:
        return None  # TODO: ReflectionProcessor.get_reflection + sessions_for_reflection

    def list_sessions(self, with_content: bool = True) -> list[dict[str, Any]]:
        return []  # TODO: ReflectionProcessor.list_sessions → serialize

    def get_session_detail(self, session_id: str) -> dict[str, Any] | None:
        return None  # TODO: ReflectionProcessor.get_session + nested reflection

    # ── Settings ─────────────────────────────────────────────────────────────

    @property
    def settings(self) -> Settings:
        return self._settings
