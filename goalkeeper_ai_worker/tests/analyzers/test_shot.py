"""Testes de worker.analyzers.shot.ShotAnalyzer - primeiro Analyzer de
EVENTOS: identifica apenas se houve um evento compativel com um chute.
Nunca detecta gol, nunca avalia defesa, nunca avalia qualidade, nunca
preve trajetoria futura - criterios deterministicos e parametrizaveis."""
from __future__ import annotations

from worker.analyzers.results import ShotAnalysisResult
from worker.analyzers.shot import ShotAnalyzer
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
_LEFT_GOAL_REGION = Region(x=0, y=200, width=20, height=100)  # goal_center = (10, 250)


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
    analyzer = ShotAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert isinstance(result, ShotAnalysisResult)
    assert result.ball_detected is False
    assert result.motion_detected is None
    assert result.shot_detected is False
    assert result.shot_start_frame is None
    assert result.ball_speed is None
    assert result.direction_vector is None
    assert result.direction_angle is None
    assert result.towards_goal is None
    assert result.distance_to_goal is None
    assert result.observation_count == 0
    assert result.confidence is None


def test_stationary_ball_is_not_a_shot() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)]))

    assert result.ball_detected is True
    assert result.motion_detected is False
    assert result.shot_detected is False
    assert result.shot_start_frame is None


def test_insufficient_speed_is_not_a_shot() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    result = analyzer.analyze(_world(1, [_ball(295, 250)]))  # speed=5, abaixo do minimo (20)

    assert result.motion_detected is True
    assert result.ball_speed == 5.0
    assert result.shot_detected is False


def test_fast_movement_away_from_goal_is_not_a_shot() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(100, 250)]))
    result = analyzer.analyze(_world(1, [_ball(130, 250)]))  # speed=30, mas afastando do gol

    assert result.ball_speed == 30.0
    assert result.towards_goal is False
    assert result.shot_detected is False


def test_single_qualifying_frame_is_not_enough_by_default() -> None:
    """WORKER_SHOT_MIN_CONSECUTIVE_FRAMES=2 (padrao) - um unico frame
    qualificante nao basta, precisa de continuidade."""
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    result = analyzer.analyze(_world(1, [_ball(275, 250)]))  # speed=25, em direcao ao gol

    assert result.ball_speed == 25.0
    assert result.towards_goal is True
    assert result.shot_detected is False  # so 1 frame qualificante ate agora
    assert result.shot_start_frame is None


def test_consecutive_qualifying_frames_detect_a_shot() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))  # 1o frame qualificante
    result = analyzer.analyze(_world(2, [_ball(250, 250)]))  # 2o frame qualificante consecutivo

    assert result.shot_detected is True
    assert result.shot_start_frame == 1  # onde a sequencia qualificante comecou, nao onde foi confirmada
    assert result.observation_count == 3
    assert result.distance_to_goal is not None
    assert result.confidence is not None


def test_shot_streak_breaks_when_criteria_stop_being_met() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 250)]))  # shot_detected=True aqui

    # bola desacelera bruscamente - quebra o criterio de velocidade
    result = analyzer.analyze(_world(3, [_ball(249, 250)]))  # speed=1

    assert result.shot_detected is False
    assert result.shot_start_frame is None


def test_composes_the_three_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_motion import BallMotionAnalyzer
    from worker.analyzers.ball_position import BallPositionAnalyzer
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer

    analyzer = ShotAnalyzer(get_settings())
    assert isinstance(analyzer._ball_motion_analyzer, BallMotionAnalyzer)
    assert isinstance(analyzer._ball_position_analyzer, BallPositionAnalyzer)
    assert isinstance(analyzer._goal_geometry_analyzer, GoalGeometryAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)]))
    assert result.ball_detected is True


def test_reset_clears_the_qualifying_streak() -> None:
    analyzer = ShotAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 250)]))  # shot_detected=True

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)]))
    assert result.shot_detected is False
    assert result.observation_count == 1  # BallMotionAnalyzer tambem foi resetado


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = ShotAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, []))

    assert result.metadata.analyzer_name == "shot"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
