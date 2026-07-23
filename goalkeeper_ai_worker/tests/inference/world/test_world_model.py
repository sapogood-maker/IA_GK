"""Testes de BasicWorldModel - usa a implementacao real (sem mock) contra
SceneAnalysisResults sinteticos."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.inference.events.types import SceneAnalysisResult, SceneEvent, SceneEventType, SceneObjectSnapshot
from worker.inference.trackers.types import BoundingBox
from worker.inference.world.world_model import BasicWorldModel


def _snapshot(track_id: int, x: int, y: int, label: str = "player", confidence: float = 0.9) -> SceneObjectSnapshot:
    return SceneObjectSnapshot(
        track_id=track_id, label=label, confidence=confidence,
        bbox=BoundingBox(x=x, y=y, width=20, height=40),
    )


def _scene_result(objects: list[SceneObjectSnapshot], frame_index: int,
                   events: list[SceneEvent] | None = None) -> SceneAnalysisResult:
    return SceneAnalysisResult(events=events or [], objects=objects, frame_index=frame_index)


def test_first_update_creates_a_new_object_with_age_one() -> None:
    model = BasicWorldModel(get_settings())

    state = model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    assert len(state.new_objects) == 1
    assert len(state.active_objects) == 1
    assert state.new_objects[0].track_id == 1
    assert state.new_objects[0].age == 1
    assert state.statistics.new_tracks == 1
    assert state.statistics.object_count == 1


def test_incremental_update_increases_age_and_frames_visible() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    state = model.update(_scene_result([_snapshot(1, 12, 10)], 1))

    assert state.active_objects[0].age == 2
    assert state.active_objects[0].frames_visible == 2
    assert state.new_objects == []  # nao e mais "novo" na segunda atualizacao


def test_object_disappearing_moves_to_lost_objects() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    state = model.update(_scene_result([], 1))

    assert state.active_objects == []
    assert len(state.lost_objects) == 1
    assert state.lost_objects[0].active is False
    assert state.lost_objects[0].frames_hidden == 1
    assert state.statistics.lost_tracks == 1


def test_object_reappearing_becomes_active_again() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 10, 10)], 0))
    model.update(_scene_result([], 1))

    state = model.update(_scene_result([_snapshot(1, 10, 10)], 2))

    assert len(state.active_objects) == 1
    assert state.active_objects[0].frames_hidden == 0
    assert state.lost_objects == []


def test_previous_bbox_is_tracked_across_updates() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    state = model.update(_scene_result([_snapshot(1, 30, 10)], 1))

    assert state.active_objects[0].bbox.x == 30
    assert state.active_objects[0].previous_bbox.x == 10


def test_velocity_and_acceleration_are_computed_across_updates() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 0, 0)], 0))
    model.update(_scene_result([_snapshot(1, 10, 0)], 1))  # desloca 10px -> speed=10

    state = model.update(_scene_result([_snapshot(1, 25, 0)], 2))  # desloca 15px -> speed=15, accel=5

    motion = state.active_objects[0].motion
    assert motion.speed == pytest.approx(15.0)
    assert motion.acceleration == pytest.approx(5.0)
    assert state.statistics.average_speed == pytest.approx(15.0)


def test_trajectory_respects_configured_max_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_WORLD_MAX_TRAJECTORY", "2")
    get_settings.cache_clear()
    model = BasicWorldModel(get_settings())

    for step in range(5):
        state = model.update(_scene_result([_snapshot(1, step * 10, 0)], step))

    assert len(state.active_objects[0].trajectory) == 2


def test_recent_events_respects_configured_history_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_WORLD_HISTORY_SIZE", "2")
    get_settings.cache_clear()
    model = BasicWorldModel(get_settings())

    for step in range(5):
        event = SceneEvent(event_type=SceneEventType.TRACK_UPDATED, track_id=1, frame_index=step)
        state = model.update(_scene_result([_snapshot(1, 0, 0)], step, events=[event]))

    assert len(state.recent_events) == 2
    assert state.recent_events[-1].frame_index == 4


def test_max_objects_evicts_oldest_lost_object_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_WORLD_MAX_OBJECTS", "2")
    get_settings.cache_clear()
    model = BasicWorldModel(get_settings())

    model.update(_scene_result([_snapshot(1, 0, 0), _snapshot(2, 100, 0)], 0))
    model.update(_scene_result([_snapshot(2, 100, 0)], 1))  # track 1 vira lost primeiro

    # track 3 aparece - com limite de 2 objetos, o mais antigo perdido (1) deve ser removido
    state = model.update(_scene_result([_snapshot(2, 100, 0), _snapshot(3, 200, 0)], 2))

    all_ids = {obj.track_id for obj in state.active_objects + state.lost_objects}
    assert 1 not in all_ids
    assert state.statistics.object_count <= 2


def test_reset_clears_all_internal_state() -> None:
    model = BasicWorldModel(get_settings())
    model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    model.reset()
    state = model.update(_scene_result([_snapshot(1, 10, 10)], 0))

    assert state.new_objects[0].age == 1
    assert state.statistics.object_count == 1
    assert state.recent_events == []
