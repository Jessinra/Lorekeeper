from typing import Literal, get_args

from pydantic import BaseModel

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

# Literal type for valid link relation types.
RelationType = Literal[
    "related_to",
    "used_in",
    "used_for",
    "used_by",
    "used_as",
    "contradicts",   # content conflicts with another memory
    "supersedes",    # newer/updated memory that replaces another
    "depends_on",    # requires or builds upon another memory
]

# Immutable set of all valid relation type strings — single source of truth.
RELATION_TYPES: frozenset[str] = frozenset(get_args(RelationType))


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
