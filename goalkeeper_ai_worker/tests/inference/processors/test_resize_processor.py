"""Testes de ResizeProcessor."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.resize_processor import ResizeProcessor
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(width: int = 64, height: int = 48) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=3, timestamp_seconds=0.3, position_seconds=0.3,
        fps=10.0, width=width, height=height, duration_seconds=1.0,
    )
    return image, metadata


def test_is_enabled_reflects_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    get_settings.cache_clear()
    assert ResizeProcessor.is_enabled(get_settings()) is True

    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "false")
    get_settings.cache_clear()
    assert ResizeProcessor.is_enabled(get_settings()) is False


def test_process_resizes_image_and_updates_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "32")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "24")
    get_settings.cache_clear()

    image, metadata = _make_frame_and_metadata()
    processor = ResizeProcessor(get_settings())
    context = ProcessorContext()

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image.shape == (24, 32, 3)
    assert result_metadata.width == 32
    assert result_metadata.height == 24
    assert result_metadata.frame_index == metadata.frame_index
    assert result_context.stats["resize"].frames_processed == 1
