"""Testes de worker.analyzers.factory.create_analyzer."""
from __future__ import annotations

import pytest

from worker.analyzers.base import Analyzer
from worker.analyzers.exceptions import AnalyzerInitializationError
from worker.analyzers.factory import create_analyzer
from worker.analyzers.registry import register_analyzer
from worker.analyzers.results import AnalysisResult
from worker.config.settings import get_settings
from worker.domain.football_world import FootballWorld


def test_create_analyzer_raises_for_unknown_name() -> None:
    settings = get_settings()
    with pytest.raises(AnalyzerInitializationError):
        create_analyzer("nao-existe", settings)


class _FailingAnalyzer(Analyzer):
    """Analyzer cuja inicializacao sempre falha - prova que factory.py
    envolve qualquer excecao de __init__ numa AnalyzerInitializationError."""

    name = "failing"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        raise RuntimeError("falha de inicializacao")

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        raise AssertionError("nunca deveria ser chamado")


def test_create_analyzer_wraps_initialization_failures() -> None:
    register_analyzer("failing-test-analyzer", _FailingAnalyzer)
    settings = get_settings()

    with pytest.raises(AnalyzerInitializationError):
        create_analyzer("failing-test-analyzer", settings)


def test_create_analyzer_resolves_goalkeeper_presence() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_presence", settings)
    assert analyzer.name == "goalkeeper_presence"


def test_create_analyzer_resolves_goal_geometry() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goal_geometry", settings)
    assert analyzer.name == "goal_geometry"


def test_create_analyzer_resolves_goalkeeper_position() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_position", settings)
    assert analyzer.name == "goalkeeper_position"


def test_create_analyzer_resolves_ball_position() -> None:
    settings = get_settings()
    analyzer = create_analyzer("ball_position", settings)
    assert analyzer.name == "ball_position"


def test_create_analyzer_resolves_goalkeeper_ball_alignment() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_ball_alignment", settings)
    assert analyzer.name == "goalkeeper_ball_alignment"


def test_create_analyzer_resolves_ball_motion() -> None:
    settings = get_settings()
    analyzer = create_analyzer("ball_motion", settings)
    assert analyzer.name == "ball_motion"


def test_create_analyzer_resolves_shot() -> None:
    settings = get_settings()
    analyzer = create_analyzer("shot", settings)
    assert analyzer.name == "shot"


def test_create_analyzer_resolves_ball_trajectory() -> None:
    settings = get_settings()
    analyzer = create_analyzer("ball_trajectory", settings)
    assert analyzer.name == "ball_trajectory"


def test_create_analyzer_resolves_play_situation() -> None:
    settings = get_settings()
    analyzer = create_analyzer("play_situation", settings)
    assert analyzer.name == "play_situation"


def test_create_analyzer_resolves_goalkeeper_decision() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_decision", settings)
    assert analyzer.name == "goalkeeper_decision"


def test_create_analyzer_resolves_goalkeeper_decision_evaluation() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_decision_evaluation", settings)
    assert analyzer.name == "goalkeeper_decision_evaluation"


def test_create_analyzer_resolves_play_outcome() -> None:
    settings = get_settings()
    analyzer = create_analyzer("play_outcome", settings)
    assert analyzer.name == "play_outcome"


def test_create_analyzer_resolves_goalkeeper_performance_evaluation() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_performance_evaluation", settings)
    assert analyzer.name == "goalkeeper_performance_evaluation"


def test_create_analyzer_resolves_goalkeeper_coaching() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_coaching", settings)
    assert analyzer.name == "goalkeeper_coaching"


def test_create_analyzer_resolves_goalkeeper_analysis_report() -> None:
    settings = get_settings()
    analyzer = create_analyzer("goalkeeper_analysis_report", settings)
    assert analyzer.name == "goalkeeper_analysis_report"
