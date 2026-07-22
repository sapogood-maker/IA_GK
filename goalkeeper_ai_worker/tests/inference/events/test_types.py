"""Testes de worker.inference.events.types - tipos proprios da API de
Eventos de Cena, nunca listas de dicionarios soltos."""
from __future__ import annotations

from worker.inference.events.types import (
    MotionState,
    SceneAnalysisResult,
    SceneEvent,
    SceneEventType,
    SceneStatistics,
    TrackLifecycle,
)


def test_scene_event_to_dict_serializes_all_fields() -> None:
    event = SceneEvent(
        event_type=SceneEventType.OBJECT_STOPPED,
        track_id=3,
        frame_index=7,
        label="goalkeeper",
        motion_state=MotionState.STOPPED,
        lifecycle=TrackLifecycle.ACTIVE,
        related_track_id=None,
    )

    payload = event.to_dict()

    assert payload == {
        "event_type": "object_stopped",
        "track_id": 3,
        "frame_index": 7,
        "label": "goalkeeper",
        "motion_state": "stopped",
        "lifecycle": "active",
        "related_track_id": None,
    }


def test_scene_analysis_result_to_dict_serializes_events_and_statistics() -> None:
    event = SceneEvent(event_type=SceneEventType.TRACK_STARTED, track_id=1, frame_index=0, label="ball")
    statistics = SceneStatistics(total_tracks_observed=1, active_tracks=1, total_events=1,
                                  events_by_type={"track_started": 1})
    result = SceneAnalysisResult(
        events=[event], frame_index=0, analyzer_name="basic", analyzer_version="1.0.0",
        duration_ms=1.5, statistics=statistics,
    )

    payload = result.to_dict()

    assert payload["frame_index"] == 0
    assert payload["analyzer_name"] == "basic"
    assert payload["analyzer_version"] == "1.0.0"
    assert payload["duration_ms"] == 1.5
    assert payload["statistics"]["total_tracks_observed"] == 1
    assert payload["statistics"]["events_by_type"] == {"track_started": 1}
    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_type"] == "track_started"


def test_scene_analysis_result_defaults_to_no_events() -> None:
    result = SceneAnalysisResult()

    assert result.events == []
    assert result.to_dict()["events"] == []
