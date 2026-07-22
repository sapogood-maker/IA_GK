"""Testes de PipelineProcessor - execução da pipeline, ordem dos Processors,
ativação/desativação."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.pipeline import PipelineProcessor
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata() -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=0, timestamp_seconds=0.0, position_seconds=0.0,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


def test_default_pipeline_runs_color_and_statistics_only() -> None:
    """Por padrao (sem resize/ROI habilitados), so Color e Statistics entram."""
    pipeline = PipelineProcessor.from_settings(get_settings())

    assert pipeline.processor_names == ["color", "statistics"]


def test_pipeline_includes_resize_and_roi_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "32")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "24")
    monkeypatch.setenv("WORKER_ENABLE_ROI", "true")
    monkeypatch.setenv("WORKER_ROI_X", "0")
    monkeypatch.setenv("WORKER_ROI_Y", "0")
    monkeypatch.setenv("WORKER_ROI_WIDTH", "10")
    monkeypatch.setenv("WORKER_ROI_HEIGHT", "10")
    get_settings.cache_clear()

    pipeline = PipelineProcessor.from_settings(get_settings())

    # ordem oficial: Color -> Resize -> ROI -> Statistics
    assert pipeline.processor_names == ["color", "resize", "roi", "statistics"]


def test_disabling_color_and_statistics_removes_them(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ENABLE_COLOR_PROCESSOR", "false")
    monkeypatch.setenv("WORKER_ENABLE_STATISTICS_PROCESSOR", "false")
    get_settings.cache_clear()

    pipeline = PipelineProcessor.from_settings(get_settings())

    assert pipeline.processor_names == []


def test_process_runs_processors_in_order_and_accumulates_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_ENABLE_RESIZE", "true")
    monkeypatch.setenv("WORKER_TARGET_WIDTH", "16")
    monkeypatch.setenv("WORKER_TARGET_HEIGHT", "12")
    get_settings.cache_clear()

    pipeline = PipelineProcessor.from_settings(get_settings())
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()

    result_image, result_metadata, result_context = pipeline.process(image, metadata, context)

    assert result_image.shape == (12, 16, 3)
    assert result_metadata.width == 16
    assert result_metadata.height == 12
    assert "color" in result_context.stats
    assert "resize" in result_context.stats
    assert "statistics" in result_context.stats
    assert result_context.stats["color"].frames_processed == 1


def test_empty_pipeline_returns_frame_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ENABLE_COLOR_PROCESSOR", "false")
    monkeypatch.setenv("WORKER_ENABLE_STATISTICS_PROCESSOR", "false")
    get_settings.cache_clear()

    pipeline = PipelineProcessor.from_settings(get_settings())
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()

    result_image, result_metadata, result_context = pipeline.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats == {}
