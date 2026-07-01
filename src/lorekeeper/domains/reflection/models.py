from pydantic import BaseModel


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
