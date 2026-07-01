"""Shared test helpers for building Lorekeeper stores from a tmp_path.

Encapsulates the standard Database + focused-stores wiring so tests don't have
to repeat the boilerplate. Use `build_stores(tmp_path)` to get a `Stores` bundle
with all five focused stores sharing a single migrated Database, and
`build_service(stores, engine, kw, settings)` to construct a `MemoryService`
without repeating its long argument list in every test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.config.repository import ConfigStore
from lorekeeper.platform.metrics.repository import MetricsStore
from lorekeeper.services.orchestrator import MemoryService


@dataclass
class Stores:
    """Bundle of all focused stores plus the shared Database."""
    db: Database
    memories: MemoryStore
    links: LinkStore
    suggestions: LinkSuggestionStore
    reflections: ReflectionStore
    metrics: MetricsStore
    config: ConfigStore


def build_stores(db_path: Path) -> Stores:
    """Build a migrated Database and all five focused stores."""
    db = Database(db_path)
    db.migrate()
    return Stores(
        db=db,
        memories=MemoryStore(db),
        links=LinkStore(db),
        suggestions=LinkSuggestionStore(db),
        reflections=ReflectionStore(db),
        metrics=MetricsStore(db),
        config=ConfigStore(db),
    )


def build_service(
    stores: Stores,
    engine: Any,
    kw: KeywordIndex,
    settings: Settings,
) -> MemoryService:
    """Construct a MemoryService from a Stores bundle — avoids long arg lists.

    Note: ``stores.suggestions`` (LinkSuggestionStore) is intentionally NOT
    passed to MemoryService.  The suggestion store is managed as a separate
    module-level singleton in server.py (``_suggestions_store``) so that
    MemoryService has no dependency on link-suggestion logic.  Handler
    functions that need it receive it as an explicit parameter.
    """
    return MemoryService(
        engine,
        stores.memories,
        stores.links,
        stores.reflections,
        stores.metrics,
        stores.config,
        kw,
        settings,
    )
