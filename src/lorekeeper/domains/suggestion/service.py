"""Suggestion domain service — link recommendation use case.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5).

LKPR-104 Phase 6b: ``accept_one`` owns the accept-suggestion transaction
boundary (insert_link + update_suggestion_status, atomic) using
``Database.transaction()``. Previously both ``dashboard/routes/suggestions.py``
and ``handlers.py`` implemented this atomicity by reaching into
``svc._conn`` directly (``SAVEPOINT``/``ROLLBACK TO``/``RELEASE``) —
a repository-boundary violation flagged in the LKPR-104 audit. Both call
sites now delegate here instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.metrics.repository import MetricsStore

if TYPE_CHECKING:
    from lorekeeper.domains.link.models import MemoryLink
    from lorekeeper.domains.suggestion.candidate import LinkCandidate, LinkCandidateGenerator
    from lorekeeper.domains.suggestion.models import LinkSuggestion
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore


class SuggestionService:
    """Link candidate recommendation and suggestion review for the Suggestion aggregate."""

    def __init__(
        self,
        candidate_generator: LinkCandidateGenerator,
        engine: LanceDBEngine,
        kw: KeywordIndex,
        memories: MemoryStore,
        links: LinkStore,
        metrics: MetricsStore,
        settings: Settings,
        db: Database,
        ns_filter: list[str] | None,
    ) -> None:
        self._candidate_generator = candidate_generator
        self._engine = engine
        self._kw = kw
        self._memories = memories
        self._links = links
        self._metrics = metrics
        self._settings = settings
        self._db = db
        self._ns_filter = ns_filter

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
        self._metrics.increment_metric_safe("lore_recommend_links")
        from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator

        effective = self._settings
        if top_k is not None:
            effective = effective.model_copy(update={"link_top_m": top_k})
            generator = LinkCandidateGenerator(
                engine=self._engine,
                memory_store=self._memories,
                link_store=self._links,
                keyword_index=self._kw,
                settings=effective,
                ns_filter=self._ns_filter,
            )
        else:
            generator = self._candidate_generator
        candidates = generator.generate(lore_id)

        return candidates

    def accept_one(
        self,
        suggestion_store: LinkSuggestionStore,
        suggestion: LinkSuggestion,
        relation_type: str,
        reason: str,
    ) -> MemoryLink:
        """Atomically create the link and mark the suggestion accepted.

        Uses a SAVEPOINT (via ``Database.transaction()``) so a failure in
        either step rolls back only this suggestion — safe to call in a loop
        over a batch without one bad item poisoning already-processed items.
        """
        with self._db.transaction():
            link = self._links.insert_link(
                source_memory_id=suggestion.source_memory_id,
                target_memory_id=suggestion.target_memory_id,
                relation_type=relation_type,
                reason=reason,
            )
            suggestion_store.update_suggestion_status(suggestion.id, "accepted")
        return link
