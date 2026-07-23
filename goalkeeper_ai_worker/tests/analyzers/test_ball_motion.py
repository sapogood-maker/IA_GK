"""Testes de worker.analyzers.ball_motion.BallMotionAnalyzer -
implementacao real (sem mock), primeiro Analyzer STATEFUL: mede so
movimento ja observado, nunca preve trajetoria, nunca avalia risco."""
from __future__ import annotations

from worker.analyzers.ball_motion import BallMotionAnalyzer
from worker.analyzers.results import BallMotionResult
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def _ball(x: float, y: float, track_id: int = 2, confidence: float = 0.7) -> Ball:
    return Ball(
        track_id=EntityId(track_id), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _world(frame_index: int, balls: list[Ball]) -> FootballWorld:
    return FootballWorld(frame_index=frame_index, balls=balls)


def test_no_ball_detected() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert isinstance(result, BallMotionResult)
    assert result.ball_detected is False
    assert result.current_position is None
    assert result.previous_position is None
    assert result.displacement is None
    assert result.velocity is None
    assert result.speed is None
    assert result.direction_vector is None
    assert result.direction_angle is None
    assert result.acceleration is None
    assert result.frames_observed == 0
    assert result.motion_detected is None
    assert result.stationary is None
    assert result.confidence is None


def test_first_observation_has_no_previous_position() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(10, 10, confidence=0.7)]))

    assert result.ball_detected is True
    assert result.current_position == Coordinate(x=10, y=10)
    assert result.previous_position is None
    assert result.displacement is None
    assert result.velocity is None
    assert result.acceleration is None
    assert result.motion_detected is None
    assert result.frames_observed == 1
    assert result.confidence == 0.7


def test_second_observation_computes_displacement_and_velocity() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    result = analyzer.analyze(_world(1, [_ball(20, 10)]))

    assert result.previous_position == Coordinate(x=10, y=10)
    assert result.current_position == Coordinate(x=20, y=10)
    assert result.displacement == 10.0
    assert result.velocity == Vector(dx=10.0, dy=0.0)
    assert result.speed == 10.0
    assert result.direction_vector == Vector(dx=1.0, dy=0.0)
    assert result.direction_angle == 0.0
    assert result.motion_detected is True
    assert result.stationary is False
    assert result.acceleration is None  # ainda nao ha velocidade anterior
    assert result.frames_observed == 2


def test_third_observation_computes_acceleration() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    analyzer.analyze(_world(1, [_ball(20, 10)]))  # speed=10
    result = analyzer.analyze(_world(2, [_ball(35, 10)]))  # speed=15

    assert result.displacement == 15.0
    assert result.speed == 15.0
    assert result.acceleration == 5.0  # 15 - 10
    assert result.frames_observed == 3


def test_stationary_ball_has_zero_displacement() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    result = analyzer.analyze(_world(1, [_ball(10, 10)]))

    assert result.displacement == 0.0
    assert result.speed == 0.0
    assert result.motion_detected is False
    assert result.stationary is True


def test_ball_disappearing_resets_continuity() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    analyzer.analyze(_world(1, [_ball(20, 10)]))

    disappeared = analyzer.analyze(_world(2, []))
    assert disappeared.ball_detected is False
    assert disappeared.frames_observed == 0


def test_ball_reappearing_after_disappearance_is_a_fresh_observation() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    analyzer.analyze(_world(1, [_ball(20, 10)]))
    analyzer.analyze(_world(2, []))  # sumiu

    reappeared = analyzer.analyze(_world(3, [_ball(500, 500)]))  # reaparece longe

    assert reappeared.ball_detected is True
    assert reappeared.previous_position is None  # nao compara com a posicao de antes do sumico
    assert reappeared.displacement is None
    assert reappeared.frames_observed == 1


def test_track_id_change_without_disappearance_is_treated_as_a_new_ball() -> None:
    """Mesmo sem a bola nunca ter sumido (sempre havia >=1 bola detectada
    em cada frame), se o track_id da bola escolhida (balls[0]) mudar,
    nao ha continuidade real - nao e a mesma bola fisica."""
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10, track_id=2)]))

    result = analyzer.analyze(_world(1, [_ball(400, 400, track_id=9)]))

    assert result.ball_detected is True
    assert result.previous_position is None
    assert result.displacement is None
    assert result.frames_observed == 1


def test_reset_clears_all_internal_state() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(10, 10)]))
    analyzer.analyze(_world(1, [_ball(20, 10)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(999, 999)]))
    assert result.previous_position is None
    assert result.displacement is None
    assert result.frames_observed == 1


def test_composes_ball_position_analyzer_internally_without_registry() -> None:
    from worker.analyzers.ball_position import BallPositionAnalyzer

    analyzer = BallMotionAnalyzer(get_settings())
    assert isinstance(analyzer._ball_position_analyzer, BallPositionAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(10, 10)]))
    assert result.ball_detected is True


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = BallMotionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert result.metadata.analyzer_name == "ball_motion"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
