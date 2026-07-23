"""Testes de worker.analyzers.play_situation.PlaySituationAnalyzer -
primeiro Analyzer COGNITIVO: classifica apenas o estado OBSERVADO da
jogada. Nunca avalia o goleiro, nunca avalia defesa, nunca julga
decisoes, nunca emite nota de qualidade."""
from __future__ import annotations

from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import PlaySituationResult
from worker.analyzers.types import PlaySituation
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal
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


def _ball(x: float, y: float, track_id: int = 2, confidence: float = 0.8) -> Ball:
    return Ball(
        track_id=EntityId(track_id), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _world(frame_index: int, balls: list[Ball], goalkeepers: list[Goalkeeper] | None = None) -> FootballWorld:
    return FootballWorld(
        frame_index=frame_index, balls=balls, goalkeepers=goalkeepers or [], goals=[_goal()], field=_field(),
    )


def test_no_ball_visible() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [_goalkeeper()]))

    assert isinstance(result, PlaySituationResult)
    assert result.situation == PlaySituation.NO_BALL_VISIBLE
    assert result.sub_state is None
    assert result.ball_detected is False
    assert result.goalkeeper_detected is True
    assert result.shot_detected is False
    assert result.trajectory_detected is False
    assert result.confidence is None


def test_no_goalkeeper_visible() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], []))

    assert result.situation == PlaySituation.NO_GOALKEEPER_VISIBLE
    assert result.ball_detected is True
    assert result.goalkeeper_detected is False


def test_no_ball_takes_priority_over_no_goalkeeper() -> None:
    """Sem bola E sem goleiro - a ausencia de bola e mais fundamental."""
    analyzer = PlaySituationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.situation == PlaySituation.NO_BALL_VISIBLE


def test_first_observation_is_unknown() -> None:
    """Primeira observacao da bola - historico insuficiente para dizer
    se esta parada ou em movimento."""
    analyzer = PlaySituationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))

    assert result.situation == PlaySituation.UNKNOWN
    assert result.sub_state is None


def test_ball_stationary() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper()]))

    assert result.situation == PlaySituation.BALL_STATIONARY
    assert result.sub_state is None  # nunca inventa uma direcao para uma bola parada


def test_ball_moving_towards_goal_but_not_a_shot() -> None:
    """Velocidade abaixo do limiar de chute (padrao 20) - ainda e so
    'bola em movimento', com o sub_state indicando a direcao."""
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    result = analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper()]))  # speed=5

    assert result.situation == PlaySituation.BALL_MOVING
    assert result.sub_state == PlaySituation.SHOT_TOWARDS_GOAL


def test_ball_moving_away_from_goal() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(100, 250)], [_goalkeeper()]))
    result = analyzer.analyze(_world(1, [_ball(130, 250)], [_goalkeeper()]))  # speed=30, afastando

    assert result.situation == PlaySituation.BALL_MOVING
    assert result.sub_state == PlaySituation.SHOT_AWAY_FROM_GOAL


def test_shot_detected_with_towards_goal_sub_state() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper()]))  # 1o frame qualificante
    result = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper()]))  # 2o frame - shot_detected

    assert result.situation == PlaySituation.SHOT_DETECTED
    assert result.sub_state == PlaySituation.SHOT_TOWARDS_GOAL
    assert result.shot_detected is True
    assert result.trajectory_detected is True
    assert result.alignment_detected is True
    assert result.confidence is not None


def test_transition_from_unknown_to_moving_to_shot() -> None:
    """Sequencia real de frames - confirma que a classificacao muda
    corretamente a cada frame conforme mais historico se acumula."""
    analyzer = PlaySituationAnalyzer(get_settings())

    r0 = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    r1 = analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper()]))
    r2 = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper()]))

    assert r0.situation == PlaySituation.UNKNOWN
    assert r1.situation == PlaySituation.BALL_MOVING  # 1o frame qualificante, ainda nao e shot
    assert r2.situation == PlaySituation.SHOT_DETECTED


def test_transition_ball_disappears_mid_sequence() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper()]))

    result = analyzer.analyze(_world(2, [], [_goalkeeper()]))  # bola sumiu

    assert result.situation == PlaySituation.NO_BALL_VISIBLE
    assert result.trajectory_detected is False


def test_composes_the_four_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
    from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
    from worker.analyzers.shot import ShotAnalyzer

    analyzer = PlaySituationAnalyzer(get_settings())
    assert isinstance(analyzer._shot_analyzer, ShotAnalyzer)
    assert isinstance(analyzer._ball_trajectory_analyzer, BallTrajectoryAnalyzer)
    assert isinstance(analyzer._goalkeeper_ball_alignment_analyzer, GoalkeeperBallAlignmentAnalyzer)
    assert isinstance(analyzer._goal_geometry_analyzer, GoalGeometryAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    assert result.ball_detected is True


def test_reset_clears_composed_analyzer_state() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper()]))
    analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper()]))  # shot_detected=True

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper()]))
    assert result.situation == PlaySituation.UNKNOWN  # primeira observacao de novo, nao SHOT_DETECTED


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = PlaySituationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "play_situation"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
