"""Testes de worker.analyzers.goalkeeper_position.GoalkeeperPositionAnalyzer
- implementacao real (sem mock), totalmente deterministica: nenhuma
avaliacao de qualidade, nenhum julgamento de "posicao correta"."""
from __future__ import annotations

from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.results import GoalkeeperPositionResult
from worker.config.settings import get_settings
from worker.domain.entities.goal import Goal
from worker.domain.entities.goalkeeper import Goalkeeper
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


def _goalkeeper(x: float = 50, y: float = 250, confidence: float = 0.9) -> Goalkeeper:
    return Goalkeeper(
        track_id=EntityId(1), label=ClassLabel("goalkeeper"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 10, y=y - 20, width=20, height=40),
        age=5, frames_visible=5, frames_hidden=0, active=True,
    )


def test_no_goalkeeper_and_no_goal() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goalkeepers=[], goals=[], field=_field())

    result = analyzer.analyze(world)

    assert isinstance(result, GoalkeeperPositionResult)
    assert result.goalkeeper_detected is False
    assert result.goal_detected is False
    assert result.distance_to_goal_center is None
    assert result.lateral_offset is None
    assert result.depth_offset is None
    assert result.angle_to_goal is None
    assert result.inside_goal_area is None
    assert result.inside_penalty_area is None
    assert result.covers_left_post is None
    assert result.covers_center is None
    assert result.covers_right_post is None
    assert result.goalkeeper_position is None
    assert result.goal_center is None
    assert result.confidence is None


def test_goal_present_but_no_goalkeeper() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goalkeepers=[], goals=[_goal()], field=_field())

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is False
    assert result.goal_detected is True
    assert result.goal_center is not None
    assert result.goalkeeper_position is None
    assert result.distance_to_goal_center is None
    assert result.confidence is None


def test_goalkeeper_present_but_no_goal() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(frame_index=0, goalkeepers=[_goalkeeper()], goals=[], field=_field())

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is True
    assert result.goal_detected is False
    assert result.goalkeeper_position is not None
    assert result.goal_center is None
    assert result.distance_to_goal_center is None
    assert result.confidence is None


def test_full_geometry_with_goalkeeper_centered_near_goal() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=7, goalkeepers=[_goalkeeper(x=50, y=250)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.goalkeeper_detected is True
    assert result.goal_detected is True
    assert result.goal_center == Coordinate(x=10, y=250)
    assert result.goalkeeper_position == Coordinate(x=50, y=250)
    assert result.distance_to_goal_center == 40.0
    assert result.lateral_offset == 0.0
    assert result.depth_offset == 40.0
    assert result.angle_to_goal == 180.0  # goleiro esta a frente do gol, olhando para -x
    assert result.covers_center is True
    assert result.covers_left_post is False
    assert result.covers_right_post is False
    assert result.inside_goal_area is True
    assert result.inside_penalty_area is True


def test_goalkeeper_far_from_goal_is_outside_both_areas() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper(x=500, y=250)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    assert result.inside_goal_area is False
    assert result.inside_penalty_area is False


def test_covers_left_and_right_post() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())

    left_world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper(x=50, y=210)], goals=[_goal()], field=_field(),
    )
    right_world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper(x=50, y=290)], goals=[_goal()], field=_field(),
    )

    left_result = analyzer.analyze(left_world)
    right_result = analyzer.analyze(right_world)

    assert left_result.covers_left_post is True
    assert left_result.covers_center is False
    assert right_result.covers_right_post is True
    assert right_result.covers_center is False


def test_confidence_is_minimum_of_goalkeeper_and_goal_geometry_confidence() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    world = FootballWorld(
        frame_index=0, goalkeepers=[_goalkeeper(confidence=0.42)], goals=[_goal()], field=_field(),
    )

    result = analyzer.analyze(world)

    # geometria do gol e bem formada (confidence 1.0) -> minimo e a confianca do goleiro
    assert result.confidence == 0.42


def test_composes_goal_geometry_analyzer_internally_without_registry() -> None:
    """Prova o padrao de composicao da W14: GoalkeeperPositionAnalyzer
    funciona standalone, sem exigir que "goal_geometry" esteja registrado
    ou ativo em WORKER_ANALYZERS - ele instancia GoalGeometryAnalyzer por
    conta propria."""
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer

    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    assert isinstance(analyzer._geometry_analyzer, GoalGeometryAnalyzer)

    world = FootballWorld(frame_index=0, goalkeepers=[_goalkeeper()], goals=[_goal()], field=_field())
    result = analyzer.analyze(world)

    assert result.goal_detected is True


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperPositionAnalyzer(get_settings())
    result = analyzer.analyze(FootballWorld(frame_index=0))

    assert result.metadata.analyzer_name == "goalkeeper_position"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
