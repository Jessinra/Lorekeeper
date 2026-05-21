from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LORE_", case_sensitive=False)

    data_dir: Path = Field(default=Path.home() / ".lorekeeper")
    log_dir: Path = Field(default=Path.home() / ".lorekeeper" / "logs")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
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
    usage_normalisation_cap: int = 100

    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "lorekeeper.db"
