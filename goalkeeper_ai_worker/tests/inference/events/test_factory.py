"""Testes de worker.inference.events.factory.create_analyzer."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.exceptions import SceneAnalysisInitializationError
from worker.inference.events.factory import create_analyzer
from worker.inference.events.registry import register_analyzer
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.trackers.types import TrackingResult


def test_create_analyzer_raises_for_unknown_name() -> None:
    settings = get_settings()
    with pytest.raises(SceneAnalysisInitializationError):
        create_analyzer("nao-existe", settings)


class _FailingAnalyzer(SceneAnalyzer):
    """SceneAnalyzer cuja inicializacao sempre falha - prova que
    factory.py envolve qualquer excecao de __init__ numa
    SceneAnalysisInitializationError."""

    name = "failing"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        raise RuntimeError("falha de inicializacao")

    def analyze(self, tracking_result: TrackingResult) -> SceneAnalysisResult:
        raise AssertionError("nunca deveria ser chamado")


def test_create_analyzer_wraps_initialization_failures() -> None:
    register_analyzer("failing-test-analyzer", _FailingAnalyzer)
    settings = get_settings()

    with pytest.raises(SceneAnalysisInitializationError):
        create_analyzer("failing-test-analyzer", settings)


def test_create_analyzer_resolves_basic() -> None:
    settings = get_settings()
    analyzer = create_analyzer("basic", settings)
    assert analyzer.name == "basic"
