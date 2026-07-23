"""Testes de worker.inference.world.registry."""
from __future__ import annotations

from worker.inference.events.types import SceneAnalysisResult
from worker.inference.world.base import WorldModel
from worker.inference.world.registry import (
    available_world_models,
    get_world_model_class,
    register_world_model,
)
from worker.inference.world.world_model import BasicWorldModel
from worker.inference.world.world_state import WorldState


def test_basic_world_model_is_registered() -> None:
    assert "basic" in available_world_models()
    assert get_world_model_class("basic") is BasicWorldModel


def test_get_world_model_class_returns_none_for_unknown_name() -> None:
    assert get_world_model_class("nao-existe") is None


class _DummyWorldModel(WorldModel):
    """WorldModel de teste - prova que registrar um WorldModel novo e
    suficiente para disponibiliza-lo via configuracao, sem alterar
    WorldModelProcessor nem factory.py."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def update(self, scene_result: SceneAnalysisResult) -> WorldState:
        return WorldState(frame_index=scene_result.frame_index)


def test_registering_a_new_world_model_makes_it_available() -> None:
    register_world_model("dummy-test-world-model", _DummyWorldModel)

    assert "dummy-test-world-model" in available_world_models()
    assert get_world_model_class("dummy-test-world-model") is _DummyWorldModel
