"""Testes de worker.timeline.event.Event."""
from __future__ import annotations

import dataclasses

import pytest

from worker.timeline.event import Event


def _make_event(**overrides) -> Event:
    defaults = dict(
        event_type="ObjectDetected",
        frame_index=3,
        timestamp_seconds=0.1,
        track_id=None,
        entity="ball",
        position={"x": 1.0, "y": 2.0},
        confidence=0.9,
    )
    defaults.update(overrides)
    return Event(**defaults)


def test_event_id_is_generated_and_unique():
    a = _make_event()
    b = _make_event()
    assert a.event_id
    assert b.event_id
    assert a.event_id != b.event_id


def test_event_is_frozen_immutable():
    event = _make_event()
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.confidence = 0.5  # type: ignore[misc]


def test_parent_event_id_defaults_to_none():
    event = _make_event()
    assert event.parent_event_id is None


def test_parent_event_id_can_reference_another_event():
    parent = _make_event()
    child = _make_event(event_type="RuleEvaluated", parent_event_id=parent.event_id)
    assert child.parent_event_id == parent.event_id


def test_to_dict_contains_all_fields():
    event = _make_event(metadata={"label": "sports ball"})
    payload = event.to_dict()
    assert payload == {
        "event_id": event.event_id,
        "event_type": "ObjectDetected",
        "frame_index": 3,
        "timestamp_seconds": 0.1,
        "track_id": None,
        "entity": "ball",
        "position": {"x": 1.0, "y": 2.0},
        "confidence": 0.9,
        "metadata": {"label": "sports ball"},
        "parent_event_id": None,
    }


def test_metadata_defaults_to_empty_dict_not_none():
    event = _make_event()
    assert event.metadata == {}
