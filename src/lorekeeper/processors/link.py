"""LinkProcessor — orchestrates link CRUD with validation, metrics, and enrichment.

Consolidates the link list/create/delete logic that was previously inline in
``dashboard/routes/links.py`` (including the ``commit()`` call, which must
not live in the presentation layer).

Lives in the processors layer (between presentation and domains) and owns
validation, metrics, and commit boundaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from lorekeeper.domains.link.models import MemoryLink
    from lorekeeper.domains.link.repository import LinkStore
    from lorekeeper.domains.link.service import LinkService
    from lorekeeper.domains.memory.repository import MemoryStore
    from lorekeeper.infra.database import Database
    from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()


class LinkProcessor:
    """Orchestrates link CRUD with validation, title enrichment, metrics, and commits.

    Single home for the link list/create/delete operations that were previously
    scattered across the dashboard routes.
    """

    def __init__(
        self,
        link_service: LinkService,
        memories: MemoryStore,
        links: LinkStore,
        metrics: MetricsStore,
        db: Database,
    ) -> None:
        self._link_service = link_service
        self._memories = memories
        self._links = links
        self._metrics = metrics
        self._db = db

    # ── list_links ──────────────────────────────────────────────────────────

    def list_links(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        """Return all links with title enrichment.

        Fetches all memory rows to build a title map, then filters out links
        to/from soft-deleted memories when ``include_deleted=False`` (the
        default). Extracted from ``dashboard/routes/links.py::list_all_links``.
        """
        raw_links = self._links.all_links()
        all_rows = self._memories.all_memory_rows(include_deleted=True)
        title_map = {r["id"]: r["title"] for r in all_rows}
        deleted_ids = {r["id"] for r in all_rows if r["soft_deleted"]}

        if not include_deleted:
            raw_links = [
                lnk
                for lnk in raw_links
                if lnk.source_memory_id not in deleted_ids
                and lnk.target_memory_id not in deleted_ids
            ]

        return [
            {
                "id": lnk.id,
                "source_memory_id": lnk.source_memory_id,
                "target_memory_id": lnk.target_memory_id,
                "relation_type": lnk.relation_type,
                "reason": lnk.reason,
                "score": lnk.score,
                "created_at": lnk.created_at,
                "updated_at": lnk.updated_at,
                "usage_count": lnk.usage_count,
                "confidence": lnk.confidence,
                "confidence_count": lnk.confidence_count,
                "source_title": title_map.get(
                    lnk.source_memory_id, lnk.source_memory_id[:12] + "…"
                ),
                "target_title": title_map.get(
                    lnk.target_memory_id, lnk.target_memory_id[:12] + "…"
                ),
            }
            for lnk in raw_links
        ]

    # ── create_link ──────────────────────────────────────────────────────────

    def create_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relation_type: str,
        reason: str,
        score: float = 1.0,
    ) -> MemoryLink:
        """Create a new link between two memories.

        Validates that both source and target memories exist, validates the
        relation type, then delegates to the link store.

        Raises:
            LookupError: If source or target memory is not found.
            ValueError: If the relation type is invalid.
        """
        if self._memories.get_memory_row(source_memory_id) is None:
            raise LookupError(f"Source memory not found: {source_memory_id}")
        if self._memories.get_memory_row(target_memory_id) is None:
            raise LookupError(f"Target memory not found: {target_memory_id}")

        self._link_service.validate_relation_type(relation_type)

        link = self._links.insert_link(
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relation_type=relation_type,
            reason=reason,
            score=score,
        )
        self._db.commit()
        return link

    # ── delete_link ──────────────────────────────────────────────────────────

    def delete_link(self, link_id: str) -> None:
        """Delete a link by ID.

        Validates that the link exists, then delegates to the link store.

        Raises:
            LookupError: If the link is not found.
        """
        existing = self._links.get_link(link_id)
        if existing is None:
            raise LookupError(f"Link not found: {link_id}")

        self._links.delete_link(link_id)
        self._db.commit()
