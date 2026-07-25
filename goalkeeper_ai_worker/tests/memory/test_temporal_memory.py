"""Testes de worker.memory.temporal_memory.TemporalMemory."""
from __future__ import annotations

import dataclasses

import pytest

from worker.memory.entity_memory import EntityMemory
from worker.memory.temporal_memory import TemporalMemory
from worker.memory.track_memory import TrackMemory


def _track(track_id: int) -> TrackMemory:
    return TrackMemory(
        track_id=track_id,
        entity="ball",
        first_seen_frame=0,
        first_seen_timestamp=0.0,
        last_seen_frame=10,
        last_seen_timestamp=1.0,
        age_seconds=1.0,
        current_motion_state="moving",
    )


def _entity() -> EntityMemory:
    return EntityMemory(entity="ball", track_ids=frozenset({1, 2}), first_seen_timestamp=0.0, last_seen_timestamp=1.0)


def test_is_frozen_immutable():
    memory = TemporalMemory()
    with pytest.raises(dataclasses.FrozenInstanceError):
        memory.source_event_count = 99  # type: ignore[misc]


def test_defaults_produce_empty_memory_not_errors():
    memory = TemporalMemory()
    payload = memory.to_dict()
    assert payload["track_memories"] == {}
    assert payload["entity_memories"] == {}
    assert payload["frame_range"] is None
    assert payload["time_range_seconds"] is None
    assert payload["source_event_count"] == 0


def test_to_dict_sorts_track_memories_by_track_id():
    memory = TemporalMemory(track_memories={3: _track(3), 1: _track(1), 2: _track(2)})
    assert list(memory.to_dict()["track_memories"].keys()) == [1, 2, 3]


def test_to_dict_sorts_entity_memories_by_key():
    memory = TemporalMemory(entity_memories={"person": _entity(), "ball": _entity()})
    assert list(memory.to_dict()["entity_memories"].keys()) == ["ball", "person"]


def test_frame_range_and_time_range_serialize_as_lists():
    memory = TemporalMemory(frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    payload = memory.to_dict()
    assert payload["frame_range"] == [0, 100]
    assert payload["time_range_seconds"] == [0.0, 10.0]
