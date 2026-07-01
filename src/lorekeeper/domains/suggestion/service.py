"""Suggestion domain service — link recommendation use case.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5).

Accept/reject batch operations for pending suggestions (currently implemented
inline in ``dashboard/routes/suggestions.py`` and ``handlers.py`` using raw
``svc._conn`` SAVEPOINT calls) are moved onto this service in Phase 6b —
that's a behavior-preserving bug fix (fixing the transaction-boundary
violation), kept separate from this phase's pure logic extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.candidate import LinkCandidate
    from lorekeeper.services.orchestrator import MemoryService


class SuggestionService:
    """Link candidate recommendation for the Suggestion aggregate."""

    def __init__(self, svc: MemoryService) -> None:
        self._svc = svc

    def recommend_links(
        self,
        lore_id: str,
        top_k: int | None = None,
    ) -> list[LinkCandidate]:
        """Return link candidates for a source memory. Never writes.

        Args:
            lore_id: Source memory to find candidates for.
            top_k: Override max candidates (default: settings.link_top_m).
        """
        svc = self._svc
        svc._increment_metric("lore_recommend_links")
        from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator

        effective = svc.settings
        if top_k is not None:
            effective = effective.model_copy(update={"link_top_m": top_k})
            generator = LinkCandidateGenerator(
                engine=svc._engine,
                memory_store=svc.memories,
                link_store=svc.links,
                keyword_index=svc._kw,
                settings=effective,
                ns_filter=svc._ns_filter,
            )
        else:
            generator = svc._link_candidate_generator
        candidates = generator.generate(lore_id)

        return candidates
