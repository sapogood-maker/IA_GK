"""Testes de worker.inference.world.world_state (WorldState/WorldStatistics)."""
from __future__ import annotations

from worker.inference.events.types import SceneEvent, SceneEventType
from worker.inference.world.object_state import ObjectState
from worker.inference.world.types import BoundingBox, ClassLabel, Confidence, Motion, ObjectId, Position
from worker.inference.world.world_state import WorldState, WorldStatistics


def _object_state(track_id: int) -> ObjectState:
    return ObjectState(
        track_id=ObjectId(track_id), label=ClassLabel("player"), confidence=Confidence(0.9),
        bbox=BoundingBox(x=10, y=10, width=20, height=40), previous_bbox=None,
        position=Position(x=20, y=30), motion=Motion(0.0, 0.0, 0.0, 0.0),
        trajectory=[Position(x=20, y=30)], age=1, frames_visible=1, frames_hidden=0,
        active=True, first_seen_frame=0, last_seen_frame=0,
    )


def test_world_state_to_dict_serializes_object_groups_and_statistics() -> None:
    event = SceneEvent(event_type=SceneEventType.TRACK_STARTED, track_id=1, frame_index=0)
    state = WorldState(
        frame_index=0,
        active_objects=[_object_state(1)],
        lost_objects=[],
        new_objects=[_object_state(1)],
        recent_events=[event],
        statistics=WorldStatistics(object_count=1, active_tracks=1, new_tracks=1, average_speed=0.0),
    )

    payload = state.to_dict()

    assert payload["frame_index"] == 0
    assert len(payload["active_objects"]) == 1
    assert payload["lost_objects"] == []
    assert len(payload["new_objects"]) == 1
    assert len(payload["recent_events"]) == 1
    assert payload["recent_events"][0]["event_type"] == "track_started"
    assert payload["statistics"] == {
        "object_count": 1, "active_tracks": 1, "lost_tracks": 0, "new_tracks": 1, "average_speed": 0.0,
    }


def test_world_state_defaults_to_empty() -> None:
    state = WorldState()

    assert state.active_objects == []
    assert state.to_dict()["active_objects"] == []
