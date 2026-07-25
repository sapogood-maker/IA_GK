"""Testes de worker.perceptual_state.track_state.TrackState."""
from __future__ import annotations

import dataclasses

import pytest

from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.state_transition import StateTransition
from worker.perceptual_state.track_state import TrackState


def _make_track_state(**overrides) -> TrackState:
    defaults = dict(
        track_id=1,
        entity="ball",
        motion_state=MotionState.STOPPED,
        motion_state_since_timestamp=8.0,
        motion_state_duration_seconds=3.8,
        motion_transition_count=5,
        last_motion_transition=StateTransition(
            dimension="motion", from_state="moving", to_state="stopped", frame_index=80, timestamp_seconds=8.0
        ),
        presence_state=PresenceState.PRESENT,
        time_since_last_seen_seconds=0.0,
        presence_transition=None,
        recovery_count=1,
    )
    defaults.update(overrides)
    return TrackState(**defaults)


def test_is_frozen_immutable():
    state = _make_track_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.recovery_count = 99  # type: ignore[misc]


def test_to_dict_serializes_enum_values_as_strings():
    state = _make_track_state()
    payload = state.to_dict()
    assert payload["motion_state"] == "stopped"
    assert payload["presence_state"] == "present"


def test_to_dict_handles_no_transitions():
    state = _make_track_state(last_motion_transition=None, presence_transition=None)
    payload = state.to_dict()
    assert payload["last_motion_transition"] is None
    assert payload["presence_transition"] is None


def test_never_has_a_validation_field():
    """Reforca a separacao de responsabilidades aprovada: TrackState so
    representa, nunca valida - nenhum campo do tipo 'has_anomalous_*'
    ou similar."""
    field_names = {f.name for f in dataclasses.fields(TrackState)}
    assert not any("anomal" in name or "valid" in name for name in field_names)
