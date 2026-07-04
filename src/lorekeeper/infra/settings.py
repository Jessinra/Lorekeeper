from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
    env_prefix="LORE_", case_sensitive=False, validate_assignment=True,
)

    data_dir: Path = Field(default=Path.home() / ".lorekeeper")
    log_dir: Path = Field(default=Path.home() / ".lorekeeper" / "logs")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    busy_timeout_ms: int = Field(
        default=5000,
        description="SQLite busy_timeout in ms — wait-for-lock before erroring"
        " (LORE_BUSY_TIMEOUT_MS)",
    )
    duplicate_threshold: float = 0.85

    # Hybrid search weights (must sum to 1.0)
    w_semantic: float = 0.45
    w_keyword: float = 0.30
    w_memory: float = 0.15
    w_usage: float = 0.10

    # Score delta
    score_bump_up: float = 0.1
    score_bump_down: float = 0.05
    score_min: float = 0.0
    score_max: float = 10.0
    soft_delete_confidence_threshold: int = 2

    # EMA
    confidence_window_size: int = 20

    search_limit: int = 5
    max_links_per_memory: int = 5
    max_search_ids: int = 50  # max IDs for lore_search(ids=[...]) — LORE_MAX_SEARCH_IDS
    max_refine_from_ids: int = 200  # max IDs for refine_from — LORE_MAX_REFINE_FROM_IDS
    usage_normalisation_cap: int = 100
    decay_lambda: float = 0.0077  # time-decay λ; 0 disables decay (LORE_DECAY_LAMBDA)
    new_memory_default_score: float = 5.0  # default score for new memories

    # Encouragement / guidance rate (0.0–1.0). 1.0 = always include guidance in write responses
    enc_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Probability of including guidance in write responses (LORE_ENC_RATE)")  # noqa: E501

    namespace: str = Field(default="shared")  # LORE_NAMESPACE — agent write namespace + read scope

    # Auto-link
    auto_link_enabled: bool = True
    auto_link_k: int = 5
    auto_link_threshold: float = 0.85

    # Link candidate pipeline (LKPR-58)
    link_top_k: int = Field(default=50, description="Cosine pre-filter: top-K before scoring")
    link_top_m: int = Field(default=10, description="Max candidates returned by lore_recommend_links")  # noqa: E501
    link_score_threshold: float = Field(default=0.3, description="Min Stage 1 weighted score to pass")  # noqa: E501

    # Stage 1 scorer weights
    link_weight_cosine: float = Field(default=0.5)
    link_weight_bm25: float = Field(default=0.3)
    link_weight_entity: float = Field(default=0.1)
    link_weight_temporal: float = Field(default=0.1)

    # Temporal scorer
    link_temporal_tau_days: float = Field(
        default=30.0, description="Decay half-life in days for temporal scorer"
    )

    # spaCy entity overlap scorer
    link_spacy_model: str = Field(
        default="en_core_web_sm", description="spaCy model for entity overlap"
    )

    # Link suggestion sweep engine (LKPR-99)
    suggest_high_confidence_score: float = Field(
        default=0.85,
        description="Min weighted score for confidence='high' tag"
        " (LORE_SUGGEST_HIGH_CONFIDENCE_SCORE)",
    )
    suggest_interval_hours: int = Field(
        default=12,
        description="Sweep interval in hours (LORE_SUGGEST_INTERVAL_HOURS)",
    )
    suggest_ttl_days: int = Field(
        default=30,
        description="TTL for unacted suggestions in days (LORE_SUGGEST_TTL_DAYS)",
    )
    suggest_poll_seconds: int = Field(
        default=300,
        description="Scheduler poll interval in seconds (LORE_SUGGEST_POLL_SECONDS)",
    )

    @property
    def lancedb_path(self) -> str:
        return str(self.data_dir / "lancedb")

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "lorekeeper.db"
