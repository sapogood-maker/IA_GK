"""Testes de worker.memory.track_memory.TrackMemory."""
from __future__ import annotations

import dataclasses

import pytest

from worker.memory.event_reference import EventReference
from worker.memory.track_memory import TrackMemory


def _make_track_memory(**overrides) -> TrackMemory:
    defaults = dict(
        track_id=1,
        entity="ball",
        first_seen_frame=0,
        first_seen_timestamp=0.0,
        last_seen_frame=100,
        last_seen_timestamp=10.0,
        age_seconds=10.0,
        current_motion_state="moving",
        motion_state_durations={"stopped": 4.2, "moving": 3.1},
        states_visited=("stopped", "moving"),
        motion_transition_count=2,
        recovery_count=1,
        last_change_frame=90,
        last_change_timestamp=9.0,
        last_relevant_event=EventReference(event_id="e9", event_type="TrackUpdated", timestamp_seconds=9.0),
    )
    defaults.update(overrides)
    return TrackMemory(**defaults)


def test_is_frozen_immutable():
    memory = _make_track_memory()
    with pytest.raises(dataclasses.FrozenInstanceError):
        memory.recovery_count = 99  # type: ignore[misc]


def test_to_dict_sorts_motion_state_durations_keys():
    memory = _make_track_memory()
    payload = memory.to_dict()
    assert list(payload["motion_state_durations"].keys()) == ["moving", "stopped"]


def test_to_dict_serializes_last_relevant_event_as_reference_dict():
    memory = _make_track_memory()
    payload = memory.to_dict()
    assert payload["last_relevant_event"] == {"event_id": "e9", "event_type": "TrackUpdated", "timestamp_seconds": 9.0}


def test_to_dict_handles_no_relevant_event():
    memory = _make_track_memory(last_relevant_event=None)
    assert memory.to_dict()["last_relevant_event"] is None


def test_defaults_produce_empty_history_not_errors():
    memory = TrackMemory(
        track_id=1,
        entity=None,
        first_seen_frame=0,
        first_seen_timestamp=None,
        last_seen_frame=0,
        last_seen_timestamp=None,
        age_seconds=None,
        current_motion_state=None,
    )
    payload = memory.to_dict()
    assert payload["motion_state_durations"] == {}
    assert payload["states_visited"] == []
    assert payload["motion_transition_count"] == 0
    assert payload["recovery_count"] == 0
