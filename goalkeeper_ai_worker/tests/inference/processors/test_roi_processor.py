"""Testes de ROIProcessor."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.roi_processor import ROIProcessor
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(width: int = 64, height: int = 48) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=0, timestamp_seconds=0.0, position_seconds=0.0,
        fps=10.0, width=width, height=height, duration_seconds=1.0,
    )
    return image, metadata


def test_is_enabled_reflects_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ENABLE_ROI", "true")
    get_settings.cache_clear()
    assert ROIProcessor.is_enabled(get_settings()) is True

    monkeypatch.setenv("WORKER_ENABLE_ROI", "false")
    get_settings.cache_clear()
    assert ROIProcessor.is_enabled(get_settings()) is False


def test_process_crops_image_and_updates_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ROI_X", "10")
    monkeypatch.setenv("WORKER_ROI_Y", "5")
    monkeypatch.setenv("WORKER_ROI_WIDTH", "20")
    monkeypatch.setenv("WORKER_ROI_HEIGHT", "15")
    get_settings.cache_clear()

    image, metadata = _make_frame_and_metadata()
    processor = ROIProcessor(get_settings())
    context = ProcessorContext()

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image.shape == (15, 20, 3)
    assert result_metadata.width == 20
    assert result_metadata.height == 15
    assert result_context.stats["roi"].frames_processed == 1
