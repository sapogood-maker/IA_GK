"""Testes de worker.inference.world.object_state.ObjectState."""
from __future__ import annotations

from worker.inference.world.object_state import ObjectState
from worker.inference.world.types import BoundingBox, ClassLabel, Confidence, Motion, ObjectId, Position


def _object_state(**overrides) -> ObjectState:
    defaults = dict(
        track_id=ObjectId(1), label=ClassLabel("player"), confidence=Confidence(0.9),
        bbox=BoundingBox(x=10, y=10, width=20, height=40), previous_bbox=None,
        position=Position(x=20, y=30), motion=Motion(0.0, 0.0, 0.0, 0.0),
        trajectory=[Position(x=20, y=30)], age=1, frames_visible=1, frames_hidden=0,
        active=True, first_seen_frame=0, last_seen_frame=0,
    )
    defaults.update(overrides)
    return ObjectState(**defaults)


def test_time_in_scene_frames_is_inclusive() -> None:
    state = _object_state(first_seen_frame=5, last_seen_frame=8)

    assert state.time_in_scene_frames == 4  # frames 5,6,7,8


def test_to_dict_serializes_all_fields() -> None:
    state = _object_state(previous_bbox=BoundingBox(x=5, y=5, width=20, height=40))

    payload = state.to_dict()

    assert payload["track_id"] == 1
    assert payload["label"] == "player"
    assert payload["confidence"] == 0.9
    assert payload["bbox"] == {"x": 10, "y": 10, "width": 20, "height": 40}
    assert payload["previous_bbox"] == {"x": 5, "y": 5, "width": 20, "height": 40}
    assert payload["position"] == {"x": 20, "y": 30}
    assert payload["trajectory"] == [{"x": 20, "y": 30}]
    assert payload["active"] is True
    assert payload["time_in_scene_frames"] == 1


def test_to_dict_handles_no_previous_bbox() -> None:
    state = _object_state(previous_bbox=None)

    assert state.to_dict()["previous_bbox"] is None
