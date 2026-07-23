"""Testes de FootballDomainProcessor - mantendo o restante do fluxo real
(frame/metadata/context reais, sem transformar a imagem, sem regra de
negocio aqui). Nao ha "mock" a fazer aqui alem do que o proprio
FootballWorldBuilder ja e - a integracao real ja e leve o suficiente
para nao precisar de stub."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.football_domain_processor import FootballDomainProcessor
from worker.inference.world.world_state import WorldState
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(frame_index: int = 7) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=frame_index, timestamp_seconds=0.7, position_seconds=0.7,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


def test_is_enabled_reflects_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKER_FOOTBALL_DOMAIN_ENABLED", raising=False)
    get_settings.cache_clear()
    assert FootballDomainProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    get_settings.cache_clear()
    assert FootballDomainProcessor.is_enabled(get_settings()) is True


def test_process_is_a_noop_when_no_world_model_ran_this_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = FootballDomainProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()  # sem nenhum WorldState acumulado

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.football_worlds == []
    assert "football_domain" not in result_context.stats


def test_process_builds_from_the_latest_world_state_and_records_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = FootballDomainProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=12)
    context = ProcessorContext()
    context.add_world_state(WorldState(frame_index=12))

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["football_domain"].frames_processed == 1
    assert len(result_context.football_worlds) == 1
    assert result_context.football_worlds[0].frame_index == 12


def test_reset_delegates_to_the_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_FOOTBALL_DOMAIN_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = FootballDomainProcessor(settings)
    context = ProcessorContext()
    context.add_world_state(WorldState(frame_index=0))
    processor.process(np.zeros((1, 1, 3), dtype=np.uint8), _make_frame_and_metadata()[1], context)
    field_before = processor._builder._context.field

    processor.reset()

    assert processor._builder._context.field is None
    assert field_before is not None
