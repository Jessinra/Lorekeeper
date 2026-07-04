from typing import Any, Literal, get_args

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


def row_to_memory(row: Any) -> Memory:
    """Convert a SQLite row dict to a Memory model."""
    return Memory(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        content=row["content"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        usage_count=row["usage_count"],
        score=row["score"],
        soft_deleted=bool(row["soft_deleted"]),
        confidence=row["confidence"],
        confidence_count=row["confidence_count"],
        last_used=row["last_used"] if "last_used" in row.keys() else None,
        namespace=row["namespace"] if "namespace" in row.keys() else "shared",
        source_type=row["source_type"] if "source_type" in row.keys() else "unknown",
    )
