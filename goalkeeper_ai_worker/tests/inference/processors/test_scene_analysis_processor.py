"""Testes de SceneAnalysisProcessor - mockar apenas a inferencia do
SceneAnalyzer, mantendo o restante do fluxo real (frame/metadata/context
reais, sem transformar a imagem, sem logica de interpretacao aqui)."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.registry import register_analyzer
from worker.inference.events.types import SceneAnalysisResult, SceneEvent, SceneEventType
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.scene_analysis_processor import SceneAnalysisProcessor
from worker.inference.trackers.types import BoundingBox, TrackedObject, TrackId, TrackingResult, TrackState
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(frame_index: int = 4) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=frame_index, timestamp_seconds=0.4, position_seconds=0.4,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


class _StubAnalyzer(SceneAnalyzer):
    """Mocka apenas a inferencia do SceneAnalyzer - devolve sempre um
    evento fixo, sem nenhuma logica real de interpretacao."""

    name = "stub-analyzer"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        self.reset_calls = 0

    def analyze(self, tracking_result: TrackingResult) -> SceneAnalysisResult:
        event = SceneEvent(event_type=SceneEventType.TRACK_STARTED, track_id=1, frame_index=0, label="ball")
        return SceneAnalysisResult(events=[event], analyzer_name=self.name, analyzer_version=self.version)

    def reset(self) -> None:
        self.reset_calls += 1


@pytest.fixture(autouse=True)
def _register_stub_analyzer() -> None:
    register_analyzer("stub-analyzer", _StubAnalyzer)


def test_is_enabled_requires_both_scene_analysis_enabled_and_analyzer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORKER_SCENE_ANALYSIS_ENABLED", raising=False)
    monkeypatch.delenv("WORKER_SCENE_ANALYZER", raising=False)
    get_settings.cache_clear()
    assert SceneAnalysisProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "stub-analyzer")
    get_settings.cache_clear()
    assert SceneAnalysisProcessor.is_enabled(get_settings()) is False  # ainda falta o interruptor mestre

    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()
    assert SceneAnalysisProcessor.is_enabled(get_settings()) is True


def test_process_is_a_noop_when_no_tracking_ran_this_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "stub-analyzer")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = SceneAnalysisProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()  # sem nenhum TrackingResult acumulado

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.scene_analysis_results == []
    assert "scene_analysis" not in result_context.stats


def test_process_analyzes_the_latest_tracking_result_and_records_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "stub-analyzer")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = SceneAnalysisProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=9)
    context = ProcessorContext()
    tracked = TrackedObject(
        track_id=TrackId(1), label="player", confidence=0.9,
        bbox=BoundingBox(1, 2, 3, 4), age=1, state=TrackState.TRACKED, frame_index=9,
    )
    context.add_tracking_result(TrackingResult(tracked_objects=[tracked], frame_index=9))

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["scene_analysis"].frames_processed == 1
    assert len(result_context.scene_analysis_results) == 1
    scene_result = result_context.scene_analysis_results[0]
    assert scene_result.analyzer_name == "stub-analyzer"
    assert len(scene_result.events) == 1
    assert result_context.scene_events_to_dict()[0]["event_type"] == "track_started"


def test_reset_delegates_to_the_analyzer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_SCENE_ANALYZER", "stub-analyzer")
    monkeypatch.setenv("WORKER_SCENE_ANALYSIS_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = SceneAnalysisProcessor(settings)
    processor.reset()

    assert processor._analyzer.reset_calls == 1
