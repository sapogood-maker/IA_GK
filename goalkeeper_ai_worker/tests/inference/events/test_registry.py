"""Testes de worker.inference.events.registry."""
from __future__ import annotations

from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.registry import (
    available_analyzers,
    get_analyzer_class,
    register_analyzer,
)
from worker.inference.events.scene_analyzer import BasicSceneAnalyzer
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.trackers.types import TrackingResult


def test_basic_scene_analyzer_is_registered() -> None:
    assert "basic" in available_analyzers()
    assert get_analyzer_class("basic") is BasicSceneAnalyzer


def test_get_analyzer_class_returns_none_for_unknown_name() -> None:
    assert get_analyzer_class("nao-existe") is None


class _DummyAnalyzer(SceneAnalyzer):
    """SceneAnalyzer de teste - prova que registrar um analisador novo e
    suficiente para disponibiliza-lo via configuracao, sem alterar
    SceneAnalysisProcessor nem factory.py."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def analyze(self, tracking_result: TrackingResult) -> SceneAnalysisResult:
        return SceneAnalysisResult(analyzer_name=self.name, analyzer_version=self.version)


def test_registering_a_new_analyzer_makes_it_available() -> None:
    register_analyzer("dummy-test-analyzer", _DummyAnalyzer)

    assert "dummy-test-analyzer" in available_analyzers()
    assert get_analyzer_class("dummy-test-analyzer") is _DummyAnalyzer
