"""Testes de worker.memory.entity_memory.EntityMemory."""
from __future__ import annotations

import dataclasses

import pytest

from worker.memory.entity_memory import EntityMemory
from worker.memory.event_reference import EventReference


def _make_entity_memory(**overrides) -> EntityMemory:
    defaults = dict(
        entity="ball",
        track_ids=frozenset({3, 1, 2}),
        first_seen_timestamp=0.0,
        last_seen_timestamp=10.0,
        combined_motion_state_durations={"stopped": 4.2},
        total_recovery_count=2,
        last_relevant_event=EventReference(event_id="e5", event_type="TrackRecovered", timestamp_seconds=5.0),
    )
    defaults.update(overrides)
    return EntityMemory(**defaults)


def test_is_frozen_immutable():
    memory = _make_entity_memory()
    with pytest.raises(dataclasses.FrozenInstanceError):
        memory.total_recovery_count = 99  # type: ignore[misc]


def test_to_dict_sorts_track_ids():
    memory = _make_entity_memory()
    assert memory.to_dict()["track_ids"] == [1, 2, 3]


def test_to_dict_serializes_last_relevant_event_as_reference_dict():
    memory = _make_entity_memory()
    payload = memory.to_dict()
    assert payload["last_relevant_event"] == {"event_id": "e5", "event_type": "TrackRecovered", "timestamp_seconds": 5.0}


def test_defaults_produce_empty_history_not_errors():
    memory = EntityMemory(entity="ball", track_ids=frozenset(), first_seen_timestamp=None, last_seen_timestamp=None)
    payload = memory.to_dict()
    assert payload["combined_motion_state_durations"] == {}
    assert payload["total_recovery_count"] == 0
    assert payload["track_ids"] == []
