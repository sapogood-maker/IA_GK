"""Testes de StatisticsProcessor."""
from __future__ import annotations

import numpy as np

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.statistics_processor import StatisticsProcessor
from worker.video.metadata import FrameMetadata


def test_is_enabled_reflects_settings() -> None:
    assert StatisticsProcessor.is_enabled(get_settings()) is True


def test_process_never_changes_the_image_or_metadata() -> None:
    image = np.full((48, 64, 3), 42, dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=7, timestamp_seconds=0.7, position_seconds=0.7,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    processor = StatisticsProcessor(get_settings())
    context = ProcessorContext()

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["statistics"].frames_processed == 1
