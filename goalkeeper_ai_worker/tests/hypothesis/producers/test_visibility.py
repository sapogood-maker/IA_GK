"""Testes de worker.hypothesis.producers.visibility."""
from __future__ import annotations

from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.producers.visibility import (
    produce_entity_visibility_hypothesis,
    produce_track_visibility_hypothesis,
)
from worker.perceptual_state.entity_state import EntityState
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


def test_track_produces_none_when_present():
    assert produce_track_visibility_hypothesis(_track_state(presence_state=PresenceState.PRESENT)) is None


def test_track_produces_hypothesis_when_ended():
    hyp = produce_track_visibility_hypothesis(
        _track_state(presence_state=PresenceState.ENDED, time_since_last_seen_seconds=2.0)
    )
    assert hyp is not None
    assert hyp.hypothesis_type == HypothesisType.VISIBILITY
    assert hyp.origin == "visibility_track"
    assert "time_since_last_seen_at_least_one_second" in hyp.matching_conditions


def test_entity_produces_none_when_active_tracks_present():
    entity_state = EntityState(entity="ball", active_track_ids=frozenset({1}), ended_track_ids=frozenset({2}))
    assert produce_entity_visibility_hypothesis(entity_state) is None


def test_entity_produces_none_when_no_ended_tracks():
    entity_state = EntityState(entity="ball", active_track_ids=frozenset(), ended_track_ids=frozenset())
    assert produce_entity_visibility_hypothesis(entity_state) is None


def test_entity_produces_hypothesis_when_all_tracks_ended():
    entity_state = EntityState(entity="ball", active_track_ids=frozenset(), ended_track_ids=frozenset({1, 2}))
    hyp = produce_entity_visibility_hypothesis(entity_state)
    assert hyp is not None
    assert hyp.hypothesis_type == HypothesisType.VISIBILITY
    assert hyp.origin == "visibility_entity"
    assert hyp.entity == "ball"


def test_track_and_entity_visibility_share_type_but_differ_in_origin():
    track_hyp = produce_track_visibility_hypothesis(_track_state(presence_state=PresenceState.ENDED))
    entity_hyp = produce_entity_visibility_hypothesis(
        EntityState(entity="ball", ended_track_ids=frozenset({1}))
    )
    assert track_hyp.hypothesis_type == entity_hyp.hypothesis_type == HypothesisType.VISIBILITY
    assert track_hyp.origin != entity_hyp.origin
