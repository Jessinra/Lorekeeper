from lorekeeper.config import Settings


def dedup_score(semantic: float, keyword: float) -> float:
    return 0.6 * semantic + 0.4 * keyword


def is_duplicate(semantic: float, keyword: float, settings: Settings) -> bool:
    return dedup_score(semantic, keyword) >= settings.duplicate_threshold
