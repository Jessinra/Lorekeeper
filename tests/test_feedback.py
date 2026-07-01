import pytest

from lorekeeper.infra.settings import Settings
from lorekeeper.services.feedback import (
    apply_score_delta,
    compute_running_confidence,
    should_soft_delete,
)

S = Settings()


class TestRunningConfidence:
    def test_first_rating_sets_value(self):
        assert compute_running_confidence(None, 0, 8, 20) == pytest.approx(8.0)

    def test_second_rating_averages(self):
        c = compute_running_confidence(8.0, 1, 6, 20)
        assert c == pytest.approx(7.0)  # (8 + (6-8)/2) = 7

    def test_window_caps_influence(self):
        # After window=20 ratings, new value has 1/20 weight
        c = compute_running_confidence(5.0, 20, 10, 20)
        assert c == pytest.approx(5.0 + (10 - 5.0) / 20)

    def test_window_does_not_exceed_cap(self):
        # count=100 > window=20: effective_count still capped at 20
        c1 = compute_running_confidence(5.0, 100, 10, 20)
        c2 = compute_running_confidence(5.0, 20, 10, 20)
        assert c1 == pytest.approx(c2)


class TestScoreDelta:
    def test_useful_bumps_up(self):
        new = apply_score_delta(5.0, True, None, S)
        assert new == pytest.approx(5.0 + S.score_bump_up)

    def test_not_useful_bumps_down(self):
        new = apply_score_delta(5.0, False, None, S)
        assert new == pytest.approx(5.0 - S.score_bump_down)

    def test_high_confidence_amplifies_useful(self):
        low = apply_score_delta(5.0, True, 2, S)
        high = apply_score_delta(5.0, True, 10, S)
        assert high > low

    def test_low_confidence_amplifies_penalty(self):
        low = apply_score_delta(5.0, False, 2, S)
        high = apply_score_delta(5.0, False, 10, S)
        assert low < high  # low confidence → bigger penalty

    def test_clamps_at_max(self):
        assert apply_score_delta(9.99, True, 10, S) == pytest.approx(S.score_max)

    def test_clamps_at_min(self):
        assert apply_score_delta(0.01, False, 1, S) == pytest.approx(S.score_min)


class TestSoftDelete:
    def test_triggers_on_low_confidence_not_useful(self):
        assert should_soft_delete(False, 2, 2) is True

    def test_does_not_trigger_when_useful(self):
        assert should_soft_delete(True, 1, 2) is False

    def test_does_not_trigger_above_threshold(self):
        assert should_soft_delete(False, 3, 2) is False

    def test_does_not_trigger_without_confidence(self):
        assert should_soft_delete(False, None, 2) is False
