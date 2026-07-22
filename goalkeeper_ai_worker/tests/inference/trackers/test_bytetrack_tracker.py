"""Testes de ByteTrackTracker - usa o algoritmo real (via
ultralytics.trackers.byte_tracker.BYTETracker, sem mock) contra
DetectionResults sinteticos que simulam um objeto se movendo levemente
entre frames - a unica forma de provar que o adaptador
DetectionResult -> BYTETracker e a conversao de volta realmente
funcionam."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.inference.detectors.types import BoundingBox as DetBoundingBox
from worker.inference.detectors.types import ClassLabel as DetClassLabel
from worker.inference.detectors.types import Confidence as DetConfidence
from worker.inference.detectors.types import Detection, DetectionResult
from worker.inference.trackers.bytetrack_tracker import ByteTrackTracker


def _detection_at(x: int, y: int, label: str = "person", confidence: float = 0.9) -> DetectionResult:
    detection = Detection(
        label=DetClassLabel(label),
        confidence=DetConfidence(confidence),
        bbox=DetBoundingBox(x=x, y=y, width=40, height=80),
    )
    return DetectionResult(detections=[detection])


def test_same_object_keeps_the_same_track_id_across_frames() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    track_ids: list[int] = []
    for step in range(5):
        result = tracker.track(_detection_at(x=10 + step * 2, y=20))
        assert len(result.tracked_objects) == 1
        track_ids.append(result.tracked_objects[0].track_id)

    assert len(set(track_ids)) == 1, f"esperava um unico track_id estavel, obteve {track_ids}"


def test_track_age_increases_across_consecutive_frames() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    ages = []
    for step in range(3):
        result = tracker.track(_detection_at(x=10 + step, y=20))
        ages.append(result.tracked_objects[0].age)

    assert ages == [1, 2, 3]


def test_track_reports_the_correct_label_and_confidence() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    result = tracker.track(_detection_at(x=5, y=5, label="ball", confidence=0.77))

    tracked = result.tracked_objects[0]
    assert tracked.label == "ball"
    assert tracked.confidence == pytest.approx(0.77, rel=1e-4)


def test_statistics_reflect_active_tracks() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    result = tracker.track(_detection_at(x=1, y=1))

    assert result.statistics.active_tracks == 1
    assert result.statistics.total_tracks == 1


def test_empty_detection_result_produces_no_tracked_objects() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    result = tracker.track(DetectionResult(detections=[]))

    assert result.tracked_objects == []


def test_reset_clears_internal_track_state() -> None:
    settings = get_settings()
    tracker = ByteTrackTracker(settings)

    for step in range(3):
        tracker.track(_detection_at(x=10 + step, y=20))

    tracker.reset()
    result = tracker.track(_detection_at(x=10, y=20))

    assert result.tracked_objects[0].age == 1
    assert result.statistics.total_tracks == 1
