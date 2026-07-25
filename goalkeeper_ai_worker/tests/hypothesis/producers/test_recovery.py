"""Testes de worker.hypothesis.producers.recovery.produce_recovery_hypothesis."""
from __future__ import annotations

from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.producers.recovery import produce_recovery_hypothesis
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.track_state import TrackState


def _track_state(**overrides) -> TrackState:
    defaults = dict(
        track_id=1,
        entity="ball",
        motion_state=MotionState.STOPPED,
        motion_state_since_timestamp=8.0,
        motion_state_duration_seconds=3.8,
        motion_transition_count=5,
        last_motion_transition=None,
        presence_state=PresenceState.PRESENT,
        time_since_last_seen_seconds=0.0,
        presence_transition=None,
        recovery_count=0,
    )
    defaults.update(overrides)
    return TrackState(**defaults)


def test_produces_none_when_recovery_count_is_zero():
    assert produce_recovery_hypothesis(_track_state(recovery_count=0)) is None


def test_produces_hypothesis_when_recovery_count_is_one():
    hyp = produce_recovery_hypothesis(_track_state(recovery_count=1))
    assert hyp is not None
    assert hyp.hypothesis_type == HypothesisType.RECOVERY
    assert hyp.origin == "recovery"
    assert hyp.matching_conditions == ("recovery_count_at_least_one",)
    assert hyp.support == 1


def test_support_increases_at_two_recoveries():
    hyp = produce_recovery_hypothesis(_track_state(recovery_count=2))
    assert "recovery_count_at_least_two" in hyp.matching_conditions
    assert hyp.support == 2


def test_can_coexist_with_stationary():
    """RECOVERY nao e mutuamente exclusiva com STATIONARY/MOVEMENT."""
    from worker.hypothesis.producers.stationary import produce_stationary_hypothesis

    track_state = _track_state(motion_state=MotionState.STOPPED, recovery_count=2)
    assert produce_recovery_hypothesis(track_state) is not None
    assert produce_stationary_hypothesis(track_state) is not None
