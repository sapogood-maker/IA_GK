"""Testes de worker.inference.registry e worker.inference.engine.create_engine -
incluindo a troca de motor sem alterar o Pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worker.config.settings import get_settings
from worker.inference.base import InferenceEngine
from worker.inference.basic_vision_engine import BasicVisionEngine
from worker.inference.engine import create_engine
from worker.inference.exceptions import EngineInitializationError
from worker.inference.fake_engine import FakeInferenceEngine
from worker.inference.registry import available_engines, get_engine_class, register_engine
from worker.state.pipeline_state import PipelineState


def test_fake_engine_is_registered() -> None:
    assert "fake" in available_engines()
    assert get_engine_class("fake") is FakeInferenceEngine


def test_basic_vision_engine_is_registered_as_default() -> None:
    assert "basic_vision" in available_engines()
    assert get_engine_class("basic_vision") is BasicVisionEngine
    assert get_settings().inference_engine == "basic_vision"


def test_create_engine_resolves_the_configured_engine() -> None:
    settings = get_settings()
    engine = create_engine("fake", settings)
    assert isinstance(engine, FakeInferenceEngine)


def test_create_engine_resolves_basic_vision_engine() -> None:
    settings = get_settings()
    engine = create_engine("basic_vision", settings)
    assert isinstance(engine, BasicVisionEngine)


def test_create_engine_raises_for_unknown_engine_name() -> None:
    settings = get_settings()
    with pytest.raises(EngineInitializationError):
        create_engine("nao-existe", settings)


class _DummyEngine(InferenceEngine):
    """Motor de teste - prova que registrar um motor novo e suficiente
    para troca-lo via configuracao, sem tocar em Pipeline/Orchestrator."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        self._settings = settings

    async def process(self, state: PipelineState) -> PipelineState:
        state.status = "DUMMY_PROCESSED"
        return state


async def test_swapping_the_active_engine_requires_only_registration_and_config() -> None:
    register_engine("dummy-test-engine", _DummyEngine)

    settings = get_settings()
    engine = create_engine("dummy-test-engine", settings)
    assert isinstance(engine, _DummyEngine)

    state = PipelineState(
        job_id="job-1", video_id="video-1", message_id="0-1", started_at=datetime.now(timezone.utc)
    )
    result = await engine.process(state)
    assert result.status == "DUMMY_PROCESSED"
