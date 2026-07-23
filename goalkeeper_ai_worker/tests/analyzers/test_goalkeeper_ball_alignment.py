"""Testes de worker.analyzers.goalkeeper_ball_alignment.GoalkeeperBallAlignmentAnalyzer
- implementacao real (sem mock), totalmente deterministica: nenhuma
avaliacao de desempenho, nenhum julgamento de posicionamento, nenhuma
deteccao de chute."""
from __future__ import annotations

from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.results import GoalkeeperBallAlignmentResult
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.goal import Goal
from worker.domain.entities.field import Field
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.direction import Direction
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId

_FIELD_REGION = Region(x=0, y=0, width=1000, height=500)
_LEFT_GOAL_REGION = Region(x=0, y=200, width=20, height=100)  # goal_center = (10, 250)


def _field() -> Field:
    return Field(region=_FIELD_REGION, direction=Direction.UNKNOWN)


def _goal() -> Goal:
    return Goal(region=_LEFT_GOAL_REGION)


def _goalkeeper(x: float = 50, y: float = 250, confidence: float = 0.9) -> Goalkeeper:
    return Goalkeeper(
        track_id=EntityId(1), label=ClassLabel("goalkeeper"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 10, y=y - 20, width=20, height=40),
        age=5, frames_visible=5, frames_hidden=0, active=True,
    )


def _ball(x: float = 200, y: float = 250, confidence: float = 0.7) -> Ball:
    return Ball(
        track_id=EntityId(2), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=3, frames_visible=3, frames_hidden=0, active=True,
    )


def test_nothing_detected() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goalkeepers=[], balls=[], goals=[], field=_field())

    result = analyzer.analyze(world)

    assert isinstance(result, GoalkeeperBallAlignmentResult)
    assert result.goalkeeper_detected is False
    assert result.ball_detected is False
    assert result.goal_detected is False
    assert result.goalkeeper_position is None
    assert result.ball_position is None
    assert result.goal_center is None
    assert result.goalkeeper_to_ball_distance is None
    assert result.ball_to_goal_distance is None
    assert result.goalkeeper_to_goal_distance is None
    assert result.goalkeeper_ball_angle is None
    assert result.ball_goal_angle is None
    assert result.goalkeeper_goal_angle is None
    assert result.alignment_offset is None
    assert result.is_between_ball_and_goal is None
    assert result.alignment_line is None
    assert result.confidence is None


def test_no_ball_but_goalkeeper_and_goal_present() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper()], balls=[], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is True
    assert result.ball_detected is False
    assert result.goal_detected is True
    assert result.goalkeeper_to_goal_distance == 40.0  # nao depende da bola
    assert result.goalkeeper_to_ball_distance is None
    assert result.ball_to_goal_distance is None
    assert result.alignment_line is None
    assert result.alignment_offset is None
    assert result.is_between_ball_and_goal is None
    assert result.confidence is None  # exige goalkeeper_result e ball_result ambos com confidence


def test_no_goalkeeper_but_ball_and_goal_present() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, goalkeepers=[], balls=[_ball()], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is False
    assert result.ball_detected is True
    assert result.goal_detected is True
    assert result.ball_to_goal_distance == 190.0  # nao depende do goleiro
    assert result.alignment_line == Vector(dx=-190.0, dy=0.0)
    assert result.goalkeeper_to_ball_distance is None
    assert result.alignment_offset is None  # exige os tres
    assert result.is_between_ball_and_goal is None


def test_no_goal_but_goalkeeper_and_ball_present() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper()], balls=[_ball()], goals=[], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is True
    assert result.ball_detected is True
    assert result.goal_detected is False
    # relacao goleiro-bola nao depende do gol
    assert result.goalkeeper_to_ball_distance == 150.0
    assert result.goalkeeper_ball_angle == 0.0
    assert result.ball_to_goal_distance is None
    assert result.goalkeeper_to_goal_distance is None
    assert result.alignment_line is None
    assert result.alignment_offset is None


def test_full_geometry_goalkeeper_perfectly_aligned() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=9,
        goalkeepers=[_goalkeeper(x=50, y=250)], balls=[_ball(x=200, y=250)],
        goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is True
    assert result.ball_detected is True
    assert result.goal_detected is True
    assert result.goalkeeper_position == Coordinate(x=50, y=250)
    assert result.ball_position == Coordinate(x=200, y=250)
    assert result.goal_center == Coordinate(x=10, y=250)
    assert result.goalkeeper_to_ball_distance == 150.0
    assert result.ball_to_goal_distance == 190.0
    assert result.goalkeeper_to_goal_distance == 40.0
    assert result.goalkeeper_ball_angle == 0.0
    assert result.ball_goal_angle == 180.0
    assert result.goalkeeper_goal_angle == 180.0
    assert result.alignment_line == Vector(dx=-190.0, dy=0.0)
    # goleiro esta exatamente sobre a reta bola->gol (mesmo y=250)
    assert result.alignment_offset == 0.0
    assert result.is_between_ball_and_goal is True


def test_goalkeeper_off_the_alignment_line() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0,
        goalkeepers=[_goalkeeper(x=50, y=300)], balls=[_ball(x=200, y=250)],
        goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.alignment_offset == 50.0
    assert result.is_between_ball_and_goal is True


def test_goalkeeper_beyond_the_goal_is_not_between() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0,
        goalkeepers=[_goalkeeper(x=0, y=250)], balls=[_ball(x=200, y=250)],
        goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.is_between_ball_and_goal is False


def test_confidence_is_minimum_of_the_two_sub_results() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0,
        goalkeepers=[_goalkeeper(confidence=0.9)], balls=[_ball(confidence=0.3)],
        goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    # goalkeeper_result.confidence = min(0.9, goal_geometry.confidence=1.0) = 0.9
    # ball_result.confidence = min(0.3, 1.0) = 0.3
    # combinado = min(0.9, 0.3) = 0.3
    assert result.confidence == 0.3


def test_composes_the_three_analyzers_internally_without_registry() -> None:
    """Prova o padrao de composicao das W14/W15/W16: GoalkeeperBallAlignmentAnalyzer
    funciona standalone, sem exigir que os outros Analyzers estejam
    registrados ou ativos em WORKER_ANALYZERS - ele instancia os tres por
    conta propria."""
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())

    from worker.analyzers.ball_position import BallPositionAnalyzer
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
    from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer

    assert isinstance(analyzer._goal_geometry_analyzer, GoalGeometryAnalyzer)
    assert isinstance(analyzer._goalkeeper_position_analyzer, GoalkeeperPositionAnalyzer)
    assert isinstance(analyzer._ball_position_analyzer, BallPositionAnalyzer)

    world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper()], balls=[_ball()], goals=[_goal()], field=_field(),
    )
    result = analyzer.analyze(world)

    assert result.goal_detected is True


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperBallAlignmentAnalyzer(get_settings())
    result = analyzer.analyze(FootballWorld(frame_index=0))

    assert result.metadata.analyzer_name == "goalkeeper_ball_alignment"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
