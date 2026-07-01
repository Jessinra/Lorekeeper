from pydantic import BaseModel


class LinkSuggestion(BaseModel):
    id: str
    source_memory_id: str
    target_memory_id: str
    source_title: str
    target_title: str
    weighted_score: float
    cosine_score: float = 0.0
    bm25_score: float = 0.0
    entity_score: float = 0.0
    temporal_score: float = 0.0
    suggested_type: str | None = None
    confidence: str = "standard"  # "standard" | "high"
    status: str = "pending"      # "pending" | "accepted" | "rejected"
    created_at: str
    updated_at: str
