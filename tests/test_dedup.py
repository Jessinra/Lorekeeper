import pytest

from lorekeeper.infra.settings import Settings
from lorekeeper.services.dedup import dedup_score, is_duplicate

S = Settings()


def test_above_threshold_is_duplicate():
    # 0.6*0.9 + 0.4*0.9 = 0.9 >= 0.85
    assert is_duplicate(0.9, 0.9, S) is True


def test_below_threshold_not_duplicate():
    # 0.6*0.5 + 0.4*0.5 = 0.5 < 0.85
    assert is_duplicate(0.5, 0.5, S) is False


def test_boundary():
    # exactly 0.85
    sem = 0.85
    kw = 0.85
    assert dedup_score(sem, kw) == pytest.approx(0.85)
    assert is_duplicate(sem, kw, S) is True


def test_unrelated_not_duplicate():
    assert is_duplicate(0.1, 0.0, S) is False
