from typing import Literal

from pydantic import BaseModel

RelationType = Literal["related_to", "used_in", "used_for", "used_by", "used_as"]


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
