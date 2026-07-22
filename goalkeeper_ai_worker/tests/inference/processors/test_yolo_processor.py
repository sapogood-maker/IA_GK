"""Testes de YOLOProcessor - mockar apenas a inferencia do Detector,
mantendo o restante do fluxo real (frame/metadata/context reais, sem
transformar a imagem)."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.detectors.base import Detector
from worker.inference.detectors.registry import register_detector
from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.yolo_processor import YOLOProcessor
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata() -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=3, timestamp_seconds=0.3, position_seconds=0.3,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


class _StubDetector(Detector):
    """Mocka apenas a inferencia do modelo - devolve sempre uma detecção
    fixa, sem carregar nenhum peso real."""

    name = "stub"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def detect(self, frame: np.ndarray) -> DetectionResult:
        detection = Detection(
            label=ClassLabel("ball"), confidence=Confidence(0.9), bbox=BoundingBox(1, 2, 3, 4)
        )
        return DetectionResult(detections=[detection], model_name=self.name, model_version=self.version)


@pytest.fixture(autouse=True)
def _register_stub_detector() -> None:
    register_detector("stub", _StubDetector)


def test_is_enabled_reflects_detector_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_DETECTOR", raising=False)
    get_settings.cache_clear()
    assert YOLOProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_DETECTOR", "stub")
    get_settings.cache_clear()
    assert YOLOProcessor.is_enabled(get_settings()) is True


def test_process_does_not_transform_the_frame_and_records_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_DETECTOR", "stub")
    get_settings.cache_clear()
    settings = get_settings()

    processor = YOLOProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["yolo"].frames_processed == 1
    assert len(result_context.detections) == 1
    assert result_context.detections[0].frame_index == metadata.frame_index
    assert result_context.detections[0].detections[0].label == "ball"
