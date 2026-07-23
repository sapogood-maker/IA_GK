"""Testes de worker.analyzers.ball_position.BallPositionAnalyzer -
implementacao real (sem mock), totalmente deterministica: nenhuma
previsao de trajetoria, nenhuma avaliacao de risco, nenhum conceito de
"bola perigosa"."""
from __future__ import annotations

from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.results import BallPositionResult
from worker.analyzers.types import GoalZone
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.goal import Goal
from worker.domain.entities.field import Field
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.direction import Direction
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId

_FIELD_REGION = Region(x=0, y=0, width=1000, height=500)
_LEFT_GOAL_REGION = Region(x=0, y=200, width=20, height=100)  # mouth spans y in [200, 300]


def _field() -> Field:
    return Field(region=_FIELD_REGION, direction=Direction.UNKNOWN)


def _goal() -> Goal:
    return Goal(region=_LEFT_GOAL_REGION)


def _ball(x: float = 10, y: float = 225, confidence: float = 0.7) -> Ball:
    return Ball(
        track_id=EntityId(2), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=3, frames_visible=3, frames_hidden=0, active=True,
    )


def test_no_ball_and_no_goal() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, balls=[], goals=[], field=_field())

    result = analyzer.analyze(world)

    assert isinstance(result, BallPositionResult)
    assert result.ball_detected is False
    assert result.goal_detected is False
    assert result.ball_position is None
    assert result.ball_bbox is None
    assert result.distance_to_goal_center is None
    assert result.lateral_offset is None
    assert result.depth_offset is None
    assert result.angle_to_goal is None
    assert result.inside_goal_area is None
    assert result.inside_penalty_area is None
    assert result.ball_region is None
    assert result.goal_center is None
    assert result.confidence is None


def test_goal_present_but_no_ball() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, balls=[], goals=[_goal()], field=_field())

    result = analyzer.analyze(world)

    assert result.ball_detected is False
    assert result.goal_detected is True
    assert result.goal_center is not None
    assert result.ball_position is None
    assert result.distance_to_goal_center is None
    assert result.confidence is None


def test_ball_present_but_no_goal() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, balls=[_ball()], goals=[], field=_field())

    result = analyzer.analyze(world)

    assert result.ball_detected is True
    assert result.goal_detected is False
    assert result.ball_position is not None
    assert result.ball_bbox is not None
    assert result.goal_center is None
    assert result.distance_to_goal_center is None
    assert result.confidence is None


def test_full_geometry_with_ball_in_front_of_goal() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=4, balls=[_ball(x=50, y=250)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.ball_detected is True
    assert result.goal_detected is True
    assert result.goal_center == Coordinate(x=10, y=250)
    assert result.ball_position == Coordinate(x=50, y=250)
    assert result.ball_bbox == Region(x=45, y=245, width=10, height=10)
    assert result.distance_to_goal_center == 40.0
    assert result.lateral_offset == 0.0
    assert result.depth_offset == 40.0
    assert result.inside_goal_area is True
    assert result.inside_penalty_area is True
    # a bola esta a frente do gol (x=50), fora da faixa fina do gol (x em [0,20]) -
    # nao intercepta nenhuma zona da grade 2x3 (caso comum)
    assert result.ball_region is None


def test_ball_region_matches_goal_zone_when_ball_overlaps_the_goal_line() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    # bola dentro da faixa fina do proprio gol (x em [0,20], y em [200,300]) -
    # unico cenario em que ball_region intercepta uma zona real
    world = FootballWorld(
        frame_index=0, balls=[_ball(x=2, y=210)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.ball_region == GoalZone.TOP_LEFT


def test_ball_far_from_goal_is_outside_areas_and_has_no_zone() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, balls=[_ball(x=500, y=250)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.inside_goal_area is False
    assert result.inside_penalty_area is False
    assert result.ball_region is None


def test_confidence_is_minimum_of_ball_and_goal_geometry_confidence() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, balls=[_ball(confidence=0.33)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.confidence == 0.33


def test_composes_goal_geometry_analyzer_internally_without_registry() -> None:
    """Prova o padrao de composicao da W14/W15: BallPositionAnalyzer
    funciona standalone, sem exigir que "goal_geometry" esteja registrado
    ou ativo em WORKER_ANALYZERS - ele instancia GoalGeometryAnalyzer por
    conta propria."""
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer

    analyzer = BallPositionAnalyzer(get_settings())
    assert isinstance(analyzer._geometry_analyzer, GoalGeometryAnalyzer)

    world = FootballWorld(frame_index=0, balls=[_ball()], goals=[_goal()], field=_field())
    result = analyzer.analyze(world)

    assert result.goal_detected is True


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = BallPositionAnalyzer(get_settings())
    result = analyzer.analyze(FootballWorld(frame_index=0))

    assert result.metadata.analyzer_name == "ball_position"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
