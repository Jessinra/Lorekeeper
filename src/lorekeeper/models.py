from pathlib import Path
from typing import Literal, get_args

import yaml
from pydantic import BaseModel

# ── Source types (hardcoded — stable, no migration needed) ─────────────

# Literal type for valid memory source types.
SourceType = Literal[
    "observed",     # extracted from conversation (default)
    "inferred",     # agent derived it
    "user_stated",  # user said it explicitly
    "consolidated", # merged from multiple memories
    "injected",     # manually added
    "unknown",      # pre-provenance (backfilled)
]

SOURCE_TYPES: frozenset[str] = frozenset(get_args(SourceType))

# Write-time source types — 'unknown' is reserved for migration backfill only;
# callers must not submit it via the public API.
WRITE_SOURCE_TYPES: frozenset[str] = SOURCE_TYPES - {"unknown"}

# ── Link relation types (config-driven for easy evolution) ──────────────

_TYPES_YAML = Path(__file__).parent / "types.yaml"

# RelationType Literal — the canonical type-hint source. When adding/
# removing types, update this Literal AND types.yaml.
# A script or startup check (test_models_sync) keeps them in sync.
RelationType = Literal[
    "references",    # mentions or cites — clean default for most links
    "depends_on",    # requires or builds upon another memory
    "supersedes",    # newer memory that replaces an older one
    "contradicts",   # content conflicts with another memory
    "part_of",       # hierarchical composition — child belongs to parent
    "derived_from",  # based on, inferred from, or generalized from another memory
    "causes",        # direct causal relationship
]

# Immutable set of all valid relation type strings — loaded from config.
# Runtime validation uses this; the Literal above is for type checkers.
RELATION_TYPES: frozenset[str]
TYPE_MIGRATION_MAP: dict[str, str]

def _load_type_config() -> tuple[frozenset[str], dict[str, str]]:
    """Load relation types from types.yaml. Falls back to Literal if file missing."""
    if not _TYPES_YAML.exists():
        # types.yaml not shipped yet — fall back to the Literal source.
        return frozenset(get_args(RelationType)), {}

    with _TYPES_YAML.open() as f:
        cfg = yaml.safe_load(f)

    types = frozenset(cfg.get("relation_types", get_args(RelationType)))
    migration_map: dict[str, str] = cfg.get("migration_map", {})
    return types, migration_map

RELATION_TYPES, TYPE_MIGRATION_MAP = _load_type_config()


class Memory(BaseModel):
    id: str
    title: str
    description: str
    content: str
    created_at: str
    updated_at: str
    usage_count: int = 0
    score: float = 1.0
    soft_deleted: bool = False
    confidence: float | None = None
    confidence_count: int = 0
    last_used: str | None = None  # ISO datetime; null → fall back to created_at for decay
    namespace: str = "shared"  # agent write namespace; reads union [namespace, "shared"]
    source_type: SourceType = "observed"  # provenance tag — write-time types only


class MemoryLink(BaseModel):
    id: str
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    reason: str
    score: float = 1.0
    created_at: str
    updated_at: str
    usage_count: int = 0
    confidence: float | None = None
    confidence_count: int = 0


class SessionRecord(BaseModel):
    session_id: str
    session_date: str | None = None
    topic: str | None = None
    task_type: str | None = None
    reviewed_at: str
    reflection_id: str | None = None


class Reflection(BaseModel):
    id: str
    created_at: str
    session_count: int
    lessons_learnt: str
    good_patterns: str | None = None
    user_profile_updates: str | None = None
    factual_discoveries: str | None = None
    summary: str
    memory_ids: str | None = None  # JSON array of lore UUIDs
