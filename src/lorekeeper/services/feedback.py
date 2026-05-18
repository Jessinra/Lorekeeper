from lorekeeper.config import Settings


def compute_running_confidence(
    current: float | None,
    count: int,
    new_value: int,
    window: int,
) -> float:
    prev = current if current is not None else float(new_value)
    effective_count = min(count + 1, window)
    return prev + (new_value - prev) / effective_count


def apply_score_delta(
    current: float,
    useful: bool,
    confidence: int | None,
    settings: Settings,
) -> float:
    if useful:
        mult = (confidence / 10.0) if confidence is not None else 1.0
        return min(settings.score_max, current + settings.score_bump_up * mult)
    mult = ((11 - confidence) / 10.0) if confidence is not None else 1.0
    return max(settings.score_min, current - settings.score_bump_down * mult)


def should_soft_delete(useful: bool, confidence: int | None, threshold: int) -> bool:
    return (not useful) and (confidence is not None) and (confidence <= threshold)
