"""Testes de worker.memory.event_reference.EventReference."""
from __future__ import annotations

import dataclasses

import pytest

from worker.memory.event_reference import EventReference


def _raw_event() -> dict:
    return {
        "event_id": "e1",
        "event_type": "ObjectDetected",
        "frame_index": 5,
        "timestamp_seconds": 0.5,
        "track_id": None,
        "entity": "ball",
        "confidence": 0.9,
        "position": {"x": 1.0, "y": 2.0},
        "metadata": {},
        "parent_event_id": None,
    }


def test_from_event_extracts_only_the_three_compact_fields():
    reference = EventReference.from_event(_raw_event())
    assert reference.event_id == "e1"
    assert reference.event_type == "ObjectDetected"
    assert reference.timestamp_seconds == 0.5


def test_is_frozen_immutable():
    reference = EventReference.from_event(_raw_event())
    with pytest.raises(dataclasses.FrozenInstanceError):
        reference.event_id = "other"  # type: ignore[misc]


def test_to_dict_round_trips_the_three_fields():
    reference = EventReference.from_event(_raw_event())
    assert reference.to_dict() == {"event_id": "e1", "event_type": "ObjectDetected", "timestamp_seconds": 0.5}


def test_never_carries_position_or_confidence_or_metadata():
    """Reforca a garantia central da W32: EventReference nunca embute o
    Event inteiro - so os 3 campos aprovados."""
    field_names = {f.name for f in dataclasses.fields(EventReference)}
    assert field_names == {"event_id", "event_type", "timestamp_seconds"}
