"""Link domain service — link CRUD business rules.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5).
"""

from __future__ import annotations

from typing import Any

from lorekeeper.domains.link.models import RELATION_TYPES
from lorekeeper.domains.link.repository import LinkStore


class LinkService:
    """Link creation and relation-type validation for the Link aggregate."""

    def __init__(self, links: LinkStore) -> None:
        self._links = links

    def insert_one_link(self, lnk: dict[str, Any]) -> dict[str, Any]:
        self.validate_relation_type(lnk.get("relation_type", ""))
        raw_score = lnk.get("score", 1.0)
        link = self._links.insert_link(
            source_memory_id=lnk["source_memory_id"],
            target_memory_id=lnk["target_memory_id"],
            relation_type=lnk["relation_type"],
            reason=lnk.get("reason", ""),
            score=float(raw_score) if raw_score is not None else 1.0,
        )
        return {
            "id": link.id,
            "source_memory_id": link.source_memory_id,
            "target_memory_id": link.target_memory_id,
            "relation_type": link.relation_type,
        }

    @staticmethod
    def validate_relation_type(relation: str) -> None:
        """Validate that relation is one of the known relation types.

        Raises ValueError with a clear message if invalid.
        Used by insert_one_link for both inline and top-level links.
        """
        if relation not in RELATION_TYPES:
            raise ValueError(
                f"invalid relation_type '{relation}': "
                f"must be one of {sorted(RELATION_TYPES)}"
            )
