"""Testes de worker.analyzers.processor.AnalyzerProcessor - mantendo o
restante do fluxo real (frame/metadata/context reais). GoalkeeperPresenceAnalyzer
e deterministico o suficiente para nao precisar de stub - a integracao
real ja e leve."""
from __future__ import annotations

import numpy as np
import pytest

from worker.analyzers.processor import AnalyzerProcessor
from worker.config.settings import get_settings
from worker.domain.entities.goal import Goal
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.region import Region
from worker.inference.processors.base import ProcessorContext
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(frame_index: int = 7) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=frame_index, timestamp_seconds=0.7, position_seconds=0.7,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


def test_is_enabled_reflects_analyzer_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_ANALYZERS", raising=False)
    get_settings.cache_clear()
    assert AnalyzerProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
    get_settings.cache_clear()
    assert AnalyzerProcessor.is_enabled(get_settings()) is True


def test_process_is_a_noop_when_no_football_world_ran_this_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
    get_settings.cache_clear()
    settings = get_settings()

    processor = AnalyzerProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()  # sem nenhum FootballWorld acumulado

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.analysis_results == []
    assert "analyzer" not in result_context.stats


def test_process_analyzes_the_latest_football_world_and_records_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence")
    get_settings.cache_clear()
    settings = get_settings()

    processor = AnalyzerProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=12)
    context = ProcessorContext()
    context.add_football_world(FootballWorld(frame_index=12))

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["analyzer"].frames_processed == 1
    assert len(result_context.analysis_results) == 1
    assert result_context.analysis_results[0].frame_index == 12
    assert result_context.analysis_results[0].metadata.analyzer_name == "goalkeeper_presence"


def test_goalkeeper_presence_and_goal_geometry_run_together(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integracao real (sem mock) dos dois Analyzers da W13/W14 rodando
    juntos sobre o mesmo FootballWorld - prova que WORKER_ANALYZERS aceita
    ambos simultaneamente, sem nenhuma mudanca no Processor."""
    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence,goal_geometry")
    get_settings.cache_clear()
    settings = get_settings()

    processor = AnalyzerProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=3)
    context = ProcessorContext()
    context.add_football_world(
        FootballWorld(frame_index=3, goals=[Goal(region=Region(x=0, y=0, width=90, height=30))])
    )

    _, _, result_context = processor.process(image, metadata, context)

    names = {result.metadata.analyzer_name for result in result_context.analysis_results}
    assert names == {"goalkeeper_presence", "goal_geometry"}

    geometry_result = next(
        r for r in result_context.analysis_results if r.metadata.analyzer_name == "goal_geometry"
    )
    assert geometry_result.goal_detected is True
    assert geometry_result.goal_width == 90


def test_multiple_active_analyzers_each_produce_a_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prova a diferenca central desta familia: WORKER_ANALYZERS aceita
    mais de um nome, e cada Analyzer ativo roda sobre o MESMO FootballWorld
    - diferente de WorldModel/FootballDomain (uma unica implementacao ativa)."""
    from worker.analyzers.base import Analyzer
    from worker.analyzers.registry import register_analyzer
    from worker.analyzers.results import AnalysisResult, AnalyzerMetadata

    class _SecondDummyAnalyzer(Analyzer):
        name = "dummy_second"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def analyze(self, football_world: FootballWorld) -> AnalysisResult:
            return AnalysisResult(
                frame_index=football_world.frame_index,
                metadata=AnalyzerMetadata(
                    analyzer_name=self.name, analyzer_version=self.version, processing_time_ms=0.0,
                ),
            )

    register_analyzer("dummy_second", _SecondDummyAnalyzer)

    monkeypatch.setenv("WORKER_ANALYZERS", "goalkeeper_presence,dummy_second")
    get_settings.cache_clear()
    settings = get_settings()

    processor = AnalyzerProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()
    context.add_football_world(FootballWorld(frame_index=1))

    _, _, result_context = processor.process(image, metadata, context)

    names = {result.metadata.analyzer_name for result in result_context.analysis_results}
    assert names == {"goalkeeper_presence", "dummy_second"}


def test_reset_delegates_to_every_active_analyzer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    from worker.analyzers.base import Analyzer
    from worker.analyzers.registry import register_analyzer
    from worker.analyzers.results import AnalysisResult, AnalyzerMetadata

    class _ResetTrackingAnalyzer(Analyzer):
        name = "reset_tracking"
        version = "0.0.1"

        def __init__(self, settings) -> None:
            pass

        def analyze(self, football_world: FootballWorld) -> AnalysisResult:
            return AnalysisResult(
                frame_index=football_world.frame_index,
                metadata=AnalyzerMetadata(
                    analyzer_name=self.name, analyzer_version=self.version, processing_time_ms=0.0,
                ),
            )

        def reset(self) -> None:
            calls.append("reset")

    register_analyzer("reset_tracking", _ResetTrackingAnalyzer)

    monkeypatch.setenv("WORKER_ANALYZERS", "reset_tracking")
    get_settings.cache_clear()
    settings = get_settings()

    processor = AnalyzerProcessor(settings)
    processor.reset()

    assert calls == ["reset"]
