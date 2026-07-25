"""Testes de worker.perceptual_state.working_state.WorkingState."""
from __future__ import annotations

import dataclasses

import pytest

from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.track_state import TrackState
from worker.perceptual_state.working_state import WorkingState


def _track(track_id: int) -> TrackState:
    return TrackState(
        track_id=track_id,
        entity="ball",
        motion_state=MotionState.MOVING,
        motion_state_since_timestamp=0.0,
        motion_state_duration_seconds=1.0,
        motion_transition_count=1,
        last_motion_transition=None,
        presence_state=PresenceState.PRESENT,
        time_since_last_seen_seconds=0.0,
        presence_transition=None,
        recovery_count=0,
    )


def test_is_frozen_immutable():
    state = WorkingState()
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.source_track_count = 99  # type: ignore[misc]


def test_defaults_produce_empty_state_not_errors():
    state = WorkingState()
    payload = state.to_dict()
    assert payload["track_states"] == {}
    assert payload["entity_states"] == {}
    assert payload["source_track_count"] == 0


def test_to_dict_sorts_track_states_by_track_id():
    state = WorkingState(track_states={3: _track(3), 1: _track(1)})
    assert list(state.to_dict()["track_states"].keys()) == [1, 3]


def test_to_dict_sorts_entity_states_by_key():
    state = WorkingState(entity_states={"person": EntityState(entity="person"), "ball": EntityState(entity="ball")})
    assert list(state.to_dict()["entity_states"].keys()) == ["ball", "person"]
