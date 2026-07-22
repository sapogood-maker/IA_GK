"""Testes de worker.inference.trackers.types - tipos proprios da API de
Tracking, nunca listas de dicionarios soltos."""
from __future__ import annotations

from worker.inference.trackers.types import (
    BoundingBox,
    ClassLabel,
    Confidence,
    TrackedObject,
    TrackId,
    TrackingResult,
    TrackingStatistics,
    TrackState,
)


def test_tracking_result_to_dict_serializes_tracked_objects() -> None:
    tracked_object = TrackedObject(
        track_id=TrackId(7),
        label=ClassLabel("goalkeeper"),
        confidence=Confidence(0.91),
        bbox=BoundingBox(x=1, y=2, width=3, height=4),
        age=5,
        state=TrackState.TRACKED,
        frame_index=10,
    )
    result = TrackingResult(
        tracked_objects=[tracked_object],
        frame_index=10,
        tracker_name="bytetrack",
        tracker_version="1.0.0",
        duration_ms=3.5,
        statistics=TrackingStatistics(total_tracks=1, active_tracks=1, lost_tracks=0, removed_tracks=0),
    )

    payload = result.to_dict()

    assert payload["frame_index"] == 10
    assert payload["tracker_name"] == "bytetrack"
    assert payload["tracker_version"] == "1.0.0"
    assert payload["duration_ms"] == 3.5
    assert payload["statistics"] == {
        "total_tracks": 1, "active_tracks": 1, "lost_tracks": 0, "removed_tracks": 0
    }
    assert payload["tracked_objects"] == [
        {
            "track_id": 7,
            "label": "goalkeeper",
            "confidence": 0.91,
            "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
            "age": 5,
            "state": "tracked",
            "frame_index": 10,
        }
    ]


def test_tracking_result_defaults_to_no_tracked_objects() -> None:
    result = TrackingResult()

    assert result.tracked_objects == []
    assert result.to_dict()["tracked_objects"] == []
