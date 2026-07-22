"""Testes de ColorProcessor."""
from __future__ import annotations

import numpy as np

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.color_processor import ColorProcessor
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata() -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[:, :, 0] = 255  # canal B = 255 (azul puro em BGR)
    metadata = FrameMetadata(
        frame_index=0, timestamp_seconds=0.0, position_seconds=0.0,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


def test_is_enabled_reflects_settings() -> None:
    settings = get_settings()
    assert ColorProcessor.is_enabled(settings) is True


def test_process_converts_bgr_to_rgb_and_records_context() -> None:
    image, metadata = _make_frame_and_metadata()
    processor = ColorProcessor(get_settings())
    context = ProcessorContext()

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image[0, 0, 0] == 0
    assert result_image[0, 0, 2] == 255
    assert result_metadata == metadata
    assert result_context.stats["color"].frames_processed == 1
