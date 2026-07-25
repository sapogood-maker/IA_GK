"""Testes de worker.hypothesis.builder.build_hypotheses - o essencial
da Sprint W34."""
from __future__ import annotations

from worker.hypothesis.builder import build_hypotheses
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.track_state import TrackState
from worker.perceptual_state.working_state import WorkingState


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


def test_empty_working_state_produces_empty_hypothesis_set():
    hyp_set = build_hypotheses(WorkingState())
    assert hyp_set.track_hypotheses == ()
    assert hyp_set.entity_hypotheses == ()
    assert hyp_set.source_track_count == 0


def test_copies_observation_metadata_from_working_state():
    working_state = WorkingState(observed_at_frame=568, observed_at_timestamp=18.9, source_track_count=1)
    hyp_set = build_hypotheses(working_state)
    assert hyp_set.observed_at_frame == 568
    assert hyp_set.observed_at_timestamp == 18.9
    assert hyp_set.source_track_count == 1


def test_stopped_track_produces_only_stationary_not_movement():
    working_state = WorkingState(track_states={1: _track_state(motion_state=MotionState.STOPPED)})
    hyp_set = build_hypotheses(working_state)
    types = {h.hypothesis_type for h in hyp_set.track_hypotheses}
    assert types == {HypothesisType.STATIONARY}


def test_track_can_produce_multiple_simultaneous_hypotheses():
    """Um track parado, ja recuperado, e nao mais visivel produz 3
    hipoteses simultaneas - nao e contradicao, sao possibilidades
    independentes (documento arquitetural, Secao 9, risco 2)."""
    track_state = _track_state(
        motion_state=MotionState.STOPPED,
        presence_state=PresenceState.ENDED,
        time_since_last_seen_seconds=5.0,
        recovery_count=2,
    )
    working_state = WorkingState(track_states={1: track_state})
    hyp_set = build_hypotheses(working_state)
    types = {h.hypothesis_type for h in hyp_set.track_hypotheses}
    assert types == {HypothesisType.STATIONARY, HypothesisType.RECOVERY, HypothesisType.VISIBILITY}
    assert len(hyp_set.track_hypotheses) == 3


def test_unknown_motion_state_produces_no_motion_hypothesis():
    working_state = WorkingState(track_states={1: _track_state(motion_state=MotionState.UNKNOWN)})
    hyp_set = build_hypotheses(working_state)
    types = {h.hypothesis_type for h in hyp_set.track_hypotheses}
    assert HypothesisType.STATIONARY not in types
    assert HypothesisType.MOVEMENT not in types


def test_entity_visibility_hypothesis_produced_when_all_tracks_ended():
    working_state = WorkingState(
        entity_states={"ball": EntityState(entity="ball", ended_track_ids=frozenset({1, 2}))}
    )
    hyp_set = build_hypotheses(working_state)
    assert len(hyp_set.entity_hypotheses) == 1
    assert hyp_set.entity_hypotheses[0].hypothesis_type == HypothesisType.VISIBILITY


def test_ordering_is_deterministic_by_track_id():
    working_state = WorkingState(
        track_states={
            3: _track_state(track_id=3, motion_state=MotionState.STOPPED),
            1: _track_state(track_id=1, motion_state=MotionState.STOPPED),
        }
    )
    hyp_set = build_hypotheses(working_state)
    track_ids = [h.track_id for h in hyp_set.track_hypotheses]
    assert track_ids == [1, 3]


def test_determinism_same_input_produces_same_output():
    working_state = WorkingState(track_states={1: _track_state()})
    first = build_hypotheses(working_state).to_dict()
    second = build_hypotheses(working_state).to_dict()
    assert first == second
