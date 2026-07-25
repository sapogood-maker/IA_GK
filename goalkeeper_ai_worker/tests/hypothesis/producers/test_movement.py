"""Testes de worker.hypothesis.producers.movement.produce_movement_hypothesis."""
from __future__ import annotations

from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.producers.movement import produce_movement_hypothesis
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.track_state import TrackState


def _track_state(**overrides) -> TrackState:
    defaults = dict(
        track_id=1,
        entity="ball",
        motion_state=MotionState.MOVING,
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


def test_produces_hypothesis_when_moving():
    hyp = produce_movement_hypothesis(_track_state(motion_state=MotionState.MOVING))
    assert hyp is not None
    assert hyp.hypothesis_type == HypothesisType.MOVEMENT
    assert hyp.origin == "movement"


def test_produces_none_when_stopped():
    assert produce_movement_hypothesis(_track_state(motion_state=MotionState.STOPPED)) is None


def test_produces_none_when_unknown():
    assert produce_movement_hypothesis(_track_state(motion_state=MotionState.UNKNOWN)) is None


def test_mutually_exclusive_with_stationary():
    """Nunca podem ambas disparar para o mesmo TrackState - motion_state
    e um unico valor por vez."""
    from worker.hypothesis.producers.stationary import produce_stationary_hypothesis

    track_state = _track_state(motion_state=MotionState.MOVING)
    assert produce_movement_hypothesis(track_state) is not None
    assert produce_stationary_hypothesis(track_state) is None
