"""Testes de worker.analyzers.ball_trajectory.BallTrajectoryAnalyzer -
modela exclusivamente a trajetoria OBSERVADA da bola. Nunca detecta gol,
nunca avalia defesa, nunca julga decisoes do goleiro, nunca preve
posicoes futuras."""
from __future__ import annotations

from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.results import BallTrajectoryResult
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.direction import Direction
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId

_FIELD_REGION = Region(x=0, y=0, width=1000, height=500)
_LEFT_GOAL_REGION = Region(x=0, y=200, width=20, height=100)


def _field() -> Field:
    return Field(region=_FIELD_REGION, direction=Direction.UNKNOWN)


def _goal() -> Goal:
    return Goal(region=_LEFT_GOAL_REGION)


def _ball(x: float, y: float, track_id: int = 2, confidence: float = 0.8) -> Ball:
    return Ball(
        track_id=EntityId(track_id), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _world(frame_index: int, balls: list[Ball]) -> FootballWorld:
    return FootballWorld(frame_index=frame_index, balls=balls, goals=[_goal()], field=_field())


def test_no_ball_detected() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert isinstance(result, BallTrajectoryResult)
    assert result.ball_detected is False
    assert result.trajectory_detected is False
    assert result.trajectory_points is None
    assert result.trajectory_length is None
    assert result.dominant_direction is None
    assert result.average_velocity is None
    assert result.direction_consistency is None
    assert result.direction_changes == 0
    assert result.linearity_score is None
    assert result.frames_observed == 0
    assert result.confidence is None


def test_first_observation_is_a_single_point_not_yet_a_trajectory() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)]))

    assert result.ball_detected is True
    assert result.trajectory_detected is False
    assert result.trajectory_points == [Coordinate(x=300, y=250)]
    assert result.trajectory_length == 0.0
    assert result.frames_observed == 1


def test_straight_line_trajectory_has_perfect_linearity_and_consistency() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))
    result = analyzer.analyze(_world(2, [_ball(250, 250)]))

    assert result.trajectory_detected is True
    assert result.frames_observed == 3
    assert result.trajectory_length == 50.0
    assert result.linearity_score == 1.0
    assert result.direction_consistency == 1.0
    assert result.direction_changes == 0
    assert result.dominant_direction == 180.0
    assert result.average_velocity == Vector(dx=-25.0, dy=0.0)
    assert result.confidence is not None


def test_trajectory_with_a_direction_change_lowers_linearity_and_consistency() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))  # segmento 1: (-25, 0)
    result = analyzer.analyze(_world(2, [_ball(275, 225)]))  # segmento 2: (0, -25) - vira 90 graus

    assert result.trajectory_length == 50.0
    assert 0.0 < result.linearity_score < 1.0
    assert 0.0 < result.direction_consistency < 1.0
    assert result.direction_changes == 1  # desvio de 90 graus >= limiar padrao (30)


def test_small_direction_deviation_is_not_counted_as_a_change() -> None:
    """WORKER_TRAJECTORY_DIRECTION_CHANGE_THRESHOLD_DEGREES=30 (padrao) -
    um desvio pequeno (ruido normal de deteccao) nao conta como mudanca."""
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))  # segmento 1: (-25, 0)
    result = analyzer.analyze(_world(2, [_ball(250, 251)]))  # segmento 2: quase reto, desvio pequeno

    assert result.direction_changes == 0


def test_stationary_ball_has_no_meaningful_direction() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)]))

    assert result.trajectory_length == 0.0
    assert result.dominant_direction is None
    assert result.linearity_score is None  # 0/0 indefinido, nunca inventado


def test_ball_disappearance_discards_the_accumulated_trajectory() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))

    result = analyzer.analyze(_world(2, []))  # bola sumiu

    assert result.ball_detected is False
    assert result.trajectory_points is None
    assert result.frames_observed == 0


def test_reappearance_starts_a_brand_new_trajectory() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))
    analyzer.analyze(_world(2, []))  # bola sumiu

    # reaparece em outra posicao - nao emenda com a trajetoria anterior
    result = analyzer.analyze(_world(3, [_ball(200, 200)]))
    assert result.trajectory_points == [Coordinate(x=200, y=200)]
    assert result.frames_observed == 1
    assert result.trajectory_detected is False

    result = analyzer.analyze(_world(4, [_ball(190, 200)]))
    assert result.trajectory_points == [Coordinate(x=200, y=200), Coordinate(x=190, y=200)]
    assert result.frames_observed == 2
    assert result.trajectory_length == 10.0


def test_track_id_change_also_starts_a_new_trajectory() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250, track_id=2)]))
    result = analyzer.analyze(_world(1, [_ball(275, 250, track_id=9)]))  # identidade diferente

    assert result.trajectory_points == [Coordinate(x=275, y=250)]
    assert result.frames_observed == 1


def test_composes_the_three_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_motion import BallMotionAnalyzer
    from worker.analyzers.ball_position import BallPositionAnalyzer
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer

    analyzer = BallTrajectoryAnalyzer(get_settings())
    assert isinstance(analyzer._ball_motion_analyzer, BallMotionAnalyzer)
    assert isinstance(analyzer._ball_position_analyzer, BallPositionAnalyzer)
    assert isinstance(analyzer._goal_geometry_analyzer, GoalGeometryAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)]))
    assert result.ball_detected is True


def test_reset_clears_the_accumulated_trajectory() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 250)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)]))
    assert result.trajectory_detected is False
    assert result.frames_observed == 1  # BallMotionAnalyzer tambem foi resetado
    assert result.trajectory_points == [Coordinate(x=300, y=250)]


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = BallTrajectoryAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert result.metadata.analyzer_name == "ball_trajectory"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
