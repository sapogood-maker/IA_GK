"""Testes de TrackingProcessor - mockar apenas a inferencia do Tracker,
mantendo o restante do fluxo real (frame/metadata/context reais, sem
transformar a imagem, sem logica de ByteTrack aqui)."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.tracking_processor import TrackingProcessor
from worker.inference.trackers.base import Tracker
from worker.inference.trackers.registry import register_tracker
from worker.inference.trackers.types import TrackingResult
from worker.inference.trackers.types import TrackedObject as TrackerTrackedObject
from worker.inference.trackers.types import BoundingBox as TrackerBoundingBox
from worker.inference.trackers.types import ClassLabel as TrackerClassLabel
from worker.inference.trackers.types import Confidence as TrackerConfidence
from worker.inference.trackers.types import TrackId, TrackState
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(frame_index: int = 5) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=frame_index, timestamp_seconds=0.5, position_seconds=0.5,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


class _StubTracker(Tracker):
    """Mocka apenas a inferencia do Tracker - devolve sempre uma trilha
    fixa, sem nenhuma logica real de associacao."""

    name = "stub-tracker"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        self.reset_calls = 0

    def track(self, detections: DetectionResult) -> TrackingResult:
        tracked = TrackerTrackedObject(
            track_id=TrackId(1),
            label=TrackerClassLabel("player"),
            confidence=TrackerConfidence(0.8),
            bbox=TrackerBoundingBox(x=1, y=2, width=3, height=4),
            age=1,
            state=TrackState.NEW,
            frame_index=0,
        )
        return TrackingResult(
            tracked_objects=[tracked], tracker_name=self.name, tracker_version=self.version
        )

    def reset(self) -> None:
        self.reset_calls += 1


@pytest.fixture(autouse=True)
def _register_stub_tracker() -> None:
    register_tracker("stub-tracker", _StubTracker)


def test_is_enabled_requires_both_tracking_enabled_and_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_TRACKING_ENABLED", raising=False)
    monkeypatch.delenv("WORKER_TRACKER", raising=False)
    get_settings.cache_clear()
    assert TrackingProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_TRACKER", "stub-tracker")
    get_settings.cache_clear()
    assert TrackingProcessor.is_enabled(get_settings()) is False  # tracking_enabled ainda False

    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()
    assert TrackingProcessor.is_enabled(get_settings()) is True


def test_process_is_a_noop_when_no_detection_ran_this_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_TRACKER", "stub-tracker")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = TrackingProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()  # sem nenhum DetectionResult acumulado

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.tracking_results == []
    assert "tracking" not in result_context.stats


def test_process_tracks_the_latest_detection_and_records_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_TRACKER", "stub-tracker")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = TrackingProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=7)
    context = ProcessorContext()
    detection = Detection(
        label=ClassLabel("player"), confidence=Confidence(0.8), bbox=BoundingBox(1, 2, 3, 4)
    )
    context.add_detection_result(DetectionResult(detections=[detection], frame_index=7))

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["tracking"].frames_processed == 1
    assert len(result_context.tracking_results) == 1
    tracking_result = result_context.tracking_results[0]
    assert tracking_result.frame_index == 7
    assert tracking_result.tracked_objects[0].track_id == 1
    assert tracking_result.tracked_objects[0].frame_index == 7  # propagado pelo Processor


def test_reset_delegates_to_the_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_TRACKER", "stub-tracker")
    monkeypatch.setenv("WORKER_TRACKING_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = TrackingProcessor(settings)
    processor.reset()

    assert processor._tracker.reset_calls == 1
