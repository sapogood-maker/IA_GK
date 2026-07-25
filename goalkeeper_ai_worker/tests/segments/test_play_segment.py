"""Testes de worker.segments.play_segment.PlaySegment."""
from __future__ import annotations

import dataclasses

import pytest

from worker.segments.play_segment import PlaySegment


def _make_segment(**overrides) -> PlaySegment:
    defaults = dict(
        segment_id="seg-1",
        start_frame=0,
        end_frame=10,
        start_timestamp=0.0,
        end_timestamp=1.0,
        duration_seconds=1.0,
        track_ids=frozenset({1, 2}),
        ball_involved=True,
        events=[{"event_id": "e1", "frame_index": 0}, {"event_id": "e2", "frame_index": 10}],
    )
    defaults.update(overrides)
    return PlaySegment(**defaults)


def test_is_frozen_immutable():
    segment = _make_segment()
    with pytest.raises(dataclasses.FrozenInstanceError):
        segment.ball_involved = False  # type: ignore[misc]


def test_to_dict_derives_event_count_from_events_length():
    segment = _make_segment()
    payload = segment.to_dict()
    assert payload["event_count"] == 2
    assert "summary" not in payload  # sem texto pronto, de proposito (ajuste aprovado da W30)


def test_to_dict_sorts_track_ids():
    segment = _make_segment(track_ids=frozenset({3, 1, 2}))
    assert segment.to_dict()["track_ids"] == [1, 2, 3]


def test_to_dict_contains_all_structural_fields():
    segment = _make_segment()
    payload = segment.to_dict()
    assert payload == {
        "segment_id": "seg-1",
        "start_frame": 0,
        "end_frame": 10,
        "start_timestamp": 0.0,
        "end_timestamp": 1.0,
        "duration_seconds": 1.0,
        "track_ids": [1, 2],
        "ball_involved": True,
        "event_count": 2,
        "events": segment.events,
    }
