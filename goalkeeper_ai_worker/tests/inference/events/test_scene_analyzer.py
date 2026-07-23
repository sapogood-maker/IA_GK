"""Testes de BasicSceneAnalyzer - usa a implementacao real (sem mock)
contra TrackingResults sinteticos, exercitando cada um dos 9 tipos de
SceneEvent."""
from __future__ import annotations

from worker.config.settings import get_settings
from worker.inference.events.scene_analyzer import BasicSceneAnalyzer
from worker.inference.events.types import MotionState, SceneEventType, TrackLifecycle
from worker.inference.trackers.types import BoundingBox, TrackedObject, TrackId, TrackingResult, TrackState


def _tracked(track_id: int, x: int, y: int, frame_index: int, label: str = "player") -> TrackedObject:
    return TrackedObject(
        track_id=TrackId(track_id), label=label, confidence=0.9,
        bbox=BoundingBox(x=x, y=y, width=20, height=40),
        age=1, state=TrackState.TRACKED, frame_index=frame_index,
    )


def _result(objects: list[TrackedObject], frame_index: int) -> TrackingResult:
    return TrackingResult(tracked_objects=objects, frame_index=frame_index)


def test_first_appearance_emits_track_started_and_object_entered_frame() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())

    result = analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    event_types = {event.event_type for event in result.events}
    assert SceneEventType.TRACK_STARTED in event_types
    assert SceneEventType.OBJECT_ENTERED_FRAME in event_types


def test_analyze_carries_object_snapshots_for_the_world_model(monkeypatch) -> None:
    """SceneEvent nao carrega bbox - o World Model (W11) depende de
    `SceneAnalysisResult.objects` para obter posicao/bbox reais."""
    analyzer = BasicSceneAnalyzer(get_settings())

    result = analyzer.analyze(_result([_tracked(1, 10, 20, 0, label="ball")], 0))

    assert len(result.objects) == 1
    snapshot = result.objects[0]
    assert snapshot.track_id == 1
    assert snapshot.label == "ball"
    assert snapshot.bbox.x == 10
    assert snapshot.bbox.y == 20


def test_continued_tracking_without_transition_emits_track_updated() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())
    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    result = analyzer.analyze(_result([_tracked(1, 12, 10, 1)], 1))

    assert any(event.event_type == SceneEventType.TRACK_UPDATED for event in result.events)


def test_motion_transition_emits_object_stopped_then_object_moving(monkeypatch) -> None:
    import os
    os.environ["WORKER_SCENE_MOTION_THRESHOLD_PX"] = "5"
    get_settings.cache_clear()
    analyzer = BasicSceneAnalyzer(get_settings())

    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))       # frame 0: TRACK_STARTED (motion=UNKNOWN)
    analyzer.analyze(_result([_tracked(1, 60, 10, 1)], 1))       # frame 1: big jump -> motion=MOVING (else-branch, TRACK_UPDATED)
    stop_result = analyzer.analyze(_result([_tracked(1, 60, 10, 2)], 2))  # frame 2: no movement -> MOVING->STOPPED

    assert any(event.event_type == SceneEventType.OBJECT_STOPPED for event in stop_result.events)

    move_result = analyzer.analyze(_result([_tracked(1, 120, 10, 3)], 3))  # frame 3: big jump -> STOPPED->MOVING

    assert any(event.event_type == SceneEventType.OBJECT_MOVING for event in move_result.events)

    del os.environ["WORKER_SCENE_MOTION_THRESHOLD_PX"]
    get_settings.cache_clear()


def test_track_disappearing_emits_track_lost_and_object_left_frame() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())
    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    result = analyzer.analyze(_result([], 1))

    event_types = {event.event_type for event in result.events}
    assert SceneEventType.TRACK_LOST in event_types
    assert SceneEventType.OBJECT_LEFT_FRAME in event_types


def test_track_reappearing_after_loss_emits_track_recovered() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())
    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))
    analyzer.analyze(_result([], 1))  # track_id 1 lost

    result = analyzer.analyze(_result([_tracked(1, 10, 10, 2)], 2))

    assert any(event.event_type == SceneEventType.TRACK_RECOVERED for event in result.events)


def test_overlapping_tracks_emit_occlusion_detected() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())

    result = analyzer.analyze(
        _result([_tracked(1, 10, 10, 0), _tracked(2, 12, 10, 0)], 0)  # quase totalmente sobrepostos
    )

    occlusion_events = [e for e in result.events if e.event_type == SceneEventType.OCCLUSION_DETECTED]
    assert len(occlusion_events) == 1
    assert occlusion_events[0].related_track_id == 2


def test_non_overlapping_tracks_do_not_emit_occlusion() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())

    result = analyzer.analyze(
        _result([_tracked(1, 10, 10, 0), _tracked(2, 500, 500, 0)], 0)
    )

    assert not any(event.event_type == SceneEventType.OCCLUSION_DETECTED for event in result.events)


def test_statistics_are_cumulative_across_calls() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())
    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    result = analyzer.analyze(_result([_tracked(1, 12, 10, 1)], 1))

    assert result.statistics.total_events >= 2  # pelo menos TRACK_STARTED+OBJECT_ENTERED_FRAME + TRACK_UPDATED
    assert result.statistics.total_tracks_observed == 1
    assert result.statistics.active_tracks == 1


def test_reset_clears_internal_observation_state() -> None:
    analyzer = BasicSceneAnalyzer(get_settings())
    analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    analyzer.reset()
    result = analyzer.analyze(_result([_tracked(1, 10, 10, 0)], 0))

    assert any(event.event_type == SceneEventType.TRACK_STARTED for event in result.events)
    assert result.statistics.total_tracks_observed == 1
