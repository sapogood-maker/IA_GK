"""Testes de worker.hypothesis.producers.stationary.produce_stationary_hypothesis."""
from __future__ import annotations

from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.producers.stationary import produce_stationary_hypothesis
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


def test_produces_hypothesis_when_stopped():
    hyp = produce_stationary_hypothesis(_track_state(motion_state=MotionState.STOPPED))
    assert hyp is not None
    assert hyp.hypothesis_type == HypothesisType.STATIONARY
    assert hyp.origin == "stationary"


def test_produces_none_when_moving():
    assert produce_stationary_hypothesis(_track_state(motion_state=MotionState.MOVING)) is None


def test_produces_none_when_unknown():
    assert produce_stationary_hypothesis(_track_state(motion_state=MotionState.UNKNOWN)) is None


def test_support_increases_with_known_duration():
    hyp = produce_stationary_hypothesis(
        _track_state(motion_state=MotionState.STOPPED, motion_state_duration_seconds=None)
    )
    assert hyp.support == 1
    assert hyp.matching_conditions == ("motion_state_is_stopped",)


def test_support_at_exact_one_second_threshold():
    hyp = produce_stationary_hypothesis(
        _track_state(motion_state=MotionState.STOPPED, motion_state_duration_seconds=1.0)
    )
    assert "duration_at_least_one_second" in hyp.matching_conditions
    assert hyp.support == 3


def test_support_just_below_one_second_threshold():
    hyp = produce_stationary_hypothesis(
        _track_state(motion_state=MotionState.STOPPED, motion_state_duration_seconds=0.999)
    )
    assert "duration_at_least_one_second" not in hyp.matching_conditions
    assert hyp.support == 2


def test_evidence_cites_only_working_state_fields():
    hyp = produce_stationary_hypothesis(_track_state(motion_state=MotionState.STOPPED))
    fields = {e.field for e in hyp.evidence}
    assert fields <= {"motion_state", "motion_state_duration_seconds"}


def test_hypothesis_id_is_deterministic():
    hyp = produce_stationary_hypothesis(_track_state(track_id=42, motion_state=MotionState.STOPPED))
    assert hyp.hypothesis_id == "stationary:track:42"
