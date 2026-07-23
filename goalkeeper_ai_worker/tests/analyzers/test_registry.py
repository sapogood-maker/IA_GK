"""Testes de worker.analyzers.registry."""
from __future__ import annotations

from worker.analyzers.ball_motion import BallMotionAnalyzer
from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.goalkeeper_analysis_report import GoalkeeperAnalysisReportAnalyzer
from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.goalkeeper_coaching import GoalkeeperCoachingAnalyzer
from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.goalkeeper_presence import GoalkeeperPresenceAnalyzer
from worker.analyzers.shot import ShotAnalyzer
from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
from worker.analyzers.registry import (
    available_analyzers,
    get_analyzer_class,
    register_analyzer,
)
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata
from worker.domain.football_world import FootballWorld


def test_goalkeeper_presence_analyzer_is_registered() -> None:
    assert "goalkeeper_presence" in available_analyzers()
    assert get_analyzer_class("goalkeeper_presence") is GoalkeeperPresenceAnalyzer


def test_goal_geometry_analyzer_is_registered() -> None:
    assert "goal_geometry" in available_analyzers()
    assert get_analyzer_class("goal_geometry") is GoalGeometryAnalyzer


def test_goalkeeper_position_analyzer_is_registered() -> None:
    assert "goalkeeper_position" in available_analyzers()
    assert get_analyzer_class("goalkeeper_position") is GoalkeeperPositionAnalyzer


def test_ball_position_analyzer_is_registered() -> None:
    assert "ball_position" in available_analyzers()
    assert get_analyzer_class("ball_position") is BallPositionAnalyzer


def test_goalkeeper_ball_alignment_analyzer_is_registered() -> None:
    assert "goalkeeper_ball_alignment" in available_analyzers()
    assert get_analyzer_class("goalkeeper_ball_alignment") is GoalkeeperBallAlignmentAnalyzer


def test_ball_motion_analyzer_is_registered() -> None:
    assert "ball_motion" in available_analyzers()
    assert get_analyzer_class("ball_motion") is BallMotionAnalyzer


def test_shot_analyzer_is_registered() -> None:
    assert "shot" in available_analyzers()
    assert get_analyzer_class("shot") is ShotAnalyzer


def test_ball_trajectory_analyzer_is_registered() -> None:
    assert "ball_trajectory" in available_analyzers()
    assert get_analyzer_class("ball_trajectory") is BallTrajectoryAnalyzer


def test_play_situation_analyzer_is_registered() -> None:
    assert "play_situation" in available_analyzers()
    assert get_analyzer_class("play_situation") is PlaySituationAnalyzer


def test_goalkeeper_decision_analyzer_is_registered() -> None:
    assert "goalkeeper_decision" in available_analyzers()
    assert get_analyzer_class("goalkeeper_decision") is GoalkeeperDecisionAnalyzer


def test_goalkeeper_decision_evaluation_analyzer_is_registered() -> None:
    assert "goalkeeper_decision_evaluation" in available_analyzers()
    assert get_analyzer_class("goalkeeper_decision_evaluation") is GoalkeeperDecisionEvaluationAnalyzer


def test_play_outcome_analyzer_is_registered() -> None:
    assert "play_outcome" in available_analyzers()
    assert get_analyzer_class("play_outcome") is PlayOutcomeAnalyzer


def test_goalkeeper_performance_evaluation_analyzer_is_registered() -> None:
    assert "goalkeeper_performance_evaluation" in available_analyzers()
    assert get_analyzer_class("goalkeeper_performance_evaluation") is GoalkeeperPerformanceEvaluationAnalyzer


def test_goalkeeper_coaching_analyzer_is_registered() -> None:
    assert "goalkeeper_coaching" in available_analyzers()
    assert get_analyzer_class("goalkeeper_coaching") is GoalkeeperCoachingAnalyzer


def test_goalkeeper_analysis_report_analyzer_is_registered() -> None:
    assert "goalkeeper_analysis_report" in available_analyzers()
    assert get_analyzer_class("goalkeeper_analysis_report") is GoalkeeperAnalysisReportAnalyzer


def test_get_analyzer_class_returns_none_for_unknown_name() -> None:
    assert get_analyzer_class("nao-existe") is None


class _DummyAnalyzer(Analyzer):
    """Analyzer de teste - prova que registrar um Analyzer novo e
    suficiente para disponibiliza-lo via configuracao, sem alterar
    AnalyzerProcessor nem factory.py."""

    name = "dummy"
    version = "0.0.1"

    def __init__(self, settings) -> None:
        pass

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        return AnalysisResult(
            frame_index=football_world.frame_index,
            metadata=AnalyzerMetadata(analyzer_name=self.name, analyzer_version=self.version, processing_time_ms=0.0),
        )


def test_registering_a_new_analyzer_makes_it_available() -> None:
    register_analyzer("dummy-test-analyzer", _DummyAnalyzer)

    assert "dummy-test-analyzer" in available_analyzers()
    assert get_analyzer_class("dummy-test-analyzer") is _DummyAnalyzer
