"""Testes de worker.inference.world.factory.create_world_model."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.world.base import WorldModel
from worker.inference.world.exceptions import WorldModelInitializationError
from worker.inference.world.factory import create_world_model
from worker.inference.world.registry import register_world_model
from worker.inference.world.world_state import WorldState


def test_create_world_model_raises_for_unknown_name() -> None:
    settings = get_settings()
    with pytest.raises(WorldModelInitializationError):
        create_world_model("nao-existe", settings)


class _FailingWorldModel(WorldModel):
    """WorldModel cuja inicializacao sempre falha - prova que factory.py
    envolve qualquer excecao de __init__ numa WorldModelInitializationError."""

    name = "failing"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        raise RuntimeError("falha de inicializacao")

    def update(self, scene_result: SceneAnalysisResult) -> WorldState:
        raise AssertionError("nunca deveria ser chamado")


def test_create_world_model_wraps_initialization_failures() -> None:
    register_world_model("failing-test-world-model", _FailingWorldModel)
    settings = get_settings()

    with pytest.raises(WorldModelInitializationError):
        create_world_model("failing-test-world-model", settings)


def test_create_world_model_resolves_basic() -> None:
    settings = get_settings()
    world_model = create_world_model("basic", settings)
    assert world_model.name == "basic"
