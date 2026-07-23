"""Testes de WorldModelProcessor - mockar apenas a inferencia do
WorldModel, mantendo o restante do fluxo real (frame/metadata/context
reais, sem transformar a imagem, sem logica de estado aqui)."""
from __future__ import annotations

import numpy as np
import pytest

from worker.config.settings import get_settings
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.world_model_processor import WorldModelProcessor
from worker.inference.world.base import WorldModel
from worker.inference.world.registry import register_world_model
from worker.inference.world.world_state import WorldState
from worker.video.metadata import FrameMetadata


def _make_frame_and_metadata(frame_index: int = 6) -> tuple[np.ndarray, FrameMetadata]:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        frame_index=frame_index, timestamp_seconds=0.6, position_seconds=0.6,
        fps=10.0, width=64, height=48, duration_seconds=1.0,
    )
    return image, metadata


class _StubWorldModel(WorldModel):
    """Mocka apenas a inferencia do WorldModel - devolve sempre um
    WorldState fixo, sem nenhuma logica real de estado."""

    name = "stub-world-model"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        self.reset_calls = 0

    def update(self, scene_result: SceneAnalysisResult) -> WorldState:
        return WorldState(frame_index=scene_result.frame_index)

    def reset(self) -> None:
        self.reset_calls += 1


@pytest.fixture(autouse=True)
def _register_stub_world_model() -> None:
    register_world_model("stub-world-model", _StubWorldModel)


def test_is_enabled_requires_both_world_model_enabled_and_world_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORKER_WORLD_MODEL_ENABLED", raising=False)
    monkeypatch.delenv("WORKER_WORLD_MODEL", raising=False)
    get_settings.cache_clear()
    assert WorldModelProcessor.is_enabled(get_settings()) is False

    monkeypatch.setenv("WORKER_WORLD_MODEL", "stub-world-model")
    get_settings.cache_clear()
    assert WorldModelProcessor.is_enabled(get_settings()) is False  # falta o interruptor mestre

    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()
    assert WorldModelProcessor.is_enabled(get_settings()) is True


def test_process_is_a_noop_when_no_scene_analysis_ran_this_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_WORLD_MODEL", "stub-world-model")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = WorldModelProcessor(settings)
    image, metadata = _make_frame_and_metadata()
    context = ProcessorContext()  # sem nenhum SceneAnalysisResult acumulado

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.world_states == []
    assert "world_model" not in result_context.stats


def test_process_updates_with_the_latest_scene_result_and_records_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_WORLD_MODEL", "stub-world-model")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = WorldModelProcessor(settings)
    image, metadata = _make_frame_and_metadata(frame_index=11)
    context = ProcessorContext()
    context.add_scene_analysis_result(SceneAnalysisResult(frame_index=11))

    result_image, result_metadata, result_context = processor.process(image, metadata, context)

    assert result_image is image
    assert result_metadata == metadata
    assert result_context.stats["world_model"].frames_processed == 1
    assert len(result_context.world_states) == 1
    assert result_context.world_states[0].frame_index == 11


def test_reset_delegates_to_the_world_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_WORLD_MODEL", "stub-world-model")
    monkeypatch.setenv("WORKER_WORLD_MODEL_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()

    processor = WorldModelProcessor(settings)
    processor.reset()

    assert processor._world_model.reset_calls == 1
