"""Testes de worker.analyzers.goalkeeper_decision.GoalkeeperDecisionAnalyzer
- primeiro Analyzer especifico do goleiro: identifica APENAS qual
decisao o goleiro aparenta estar executando. Nunca avalia se a decisao
foi correta, nunca da nota, nunca julga desempenho."""
from __future__ import annotations

from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.results import GoalkeeperDecisionResult
from worker.analyzers.types import GoalkeeperDecision, PlaySituation
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


def _goalkeeper(x: float, y: float, track_id: int = 1, confidence: float = 0.9) -> Goalkeeper:
    return Goalkeeper(
        track_id=EntityId(track_id), label=ClassLabel("goalkeeper"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 10, y=y - 20, width=20, height=40),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _ball(x: float, y: float, track_id: int = 2, confidence: float = 0.8) -> Ball:
    return Ball(
        track_id=EntityId(track_id), label=ClassLabel("sports ball"), confidence=Confidence(confidence),
        position=Coordinate(x=x, y=y), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=x - 5, y=y - 5, width=10, height=10),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _world(
    frame_index: int, balls: list[Ball], goalkeepers: list[Goalkeeper] | None = None,
) -> FootballWorld:
    return FootballWorld(
        frame_index=frame_index, balls=balls, goalkeepers=goalkeepers or [], goals=[_goal()], field=_field(),
    )


def test_no_goalkeeper_visible() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], []))

    assert isinstance(result, GoalkeeperDecisionResult)
    assert result.decision == GoalkeeperDecision.UNKNOWN
    assert result.play_situation == PlaySituation.NO_GOALKEEPER_VISIBLE
    assert result.goalkeeper_detected is False
    assert result.goalkeeper_position is None
    assert result.movement_direction is None
    assert result.movement_speed is None
    assert result.confidence is None


def test_no_ball_visible_still_classifies_goalkeeper_behavior() -> None:
    """Sem bola, ausencia de bola tem prioridade na classificacao de
    play_situation, mas o comportamento do PROPRIO goleiro ainda pode
    ser classificado (aqui, parado)."""
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [], [_goalkeeper(50, 250)]))

    assert result.play_situation == PlaySituation.NO_BALL_VISIBLE
    assert result.goalkeeper_detected is True
    assert result.decision == GoalkeeperDecision.STAY_ON_LINE


def test_no_ball_and_no_goalkeeper() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.play_situation == PlaySituation.NO_BALL_VISIBLE  # prioridade sobre NO_GOALKEEPER_VISIBLE
    assert result.decision == GoalkeeperDecision.UNKNOWN


def test_first_observation_is_unknown() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.decision == GoalkeeperDecision.UNKNOWN
    assert result.goalkeeper_position == Coordinate(x=50, y=250)


def test_stay_on_line() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.decision == GoalkeeperDecision.STAY_ON_LINE
    assert result.movement_speed == 0.0


def test_step_forward() -> None:
    """Goleiro se afasta da linha do gol (profundidade aumenta)."""
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(20, 250)]))  # depth_offset=10
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(35, 250)]))  # depth_offset=25

    assert result.decision == GoalkeeperDecision.STEP_FORWARD


def test_step_back() -> None:
    """Goleiro se aproxima da linha do gol (profundidade diminui)."""
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(35, 250)]))  # depth_offset=25
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(20, 250)]))  # depth_offset=10

    assert result.decision == GoalkeeperDecision.STEP_BACK


def test_shift_left() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(50, 230)]))  # dy=-20

    assert result.decision == GoalkeeperDecision.SHIFT_LEFT


def test_shift_right() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(50, 270)]))  # dy=+20

    assert result.decision == GoalkeeperDecision.SHIFT_RIGHT


def test_ambiguous_tie_between_lateral_and_depth_favors_lateral() -> None:
    """Cenario ambiguo: deslocamento lateral e em profundidade com a
    MESMA magnitude - o desempate deterministico favorece a
    classificacao lateral (SHIFT_*), documentado em
    GoalkeeperDecisionAnalyzer._classify."""
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(60, 260)]))  # dx=10, dy=10

    assert result.decision == GoalkeeperDecision.SHIFT_RIGHT


def test_prepare_dive_when_shot_detected_but_movement_below_dive_threshold() -> None:
    """Chute detectado, mas o goleiro ainda nao se moveu rapido o
    suficiente para contar como um mergulho - PREPARE_DIVE e um PROXY
    deterministico, nao uma deteccao real de postura corporal."""
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))  # 1o frame qualificante
    result = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 255)]))  # shot_detected=True, dy=5

    assert result.play_situation == PlaySituation.SHOT_DETECTED
    assert result.decision == GoalkeeperDecision.PREPARE_DIVE


def test_dive_left_when_shot_detected_and_fast_lateral_movement() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 217)]))  # dy=-33

    assert result.decision == GoalkeeperDecision.DIVE_LEFT


def test_dive_right_when_shot_detected_and_fast_lateral_movement() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 283)]))  # dy=+33

    assert result.decision == GoalkeeperDecision.DIVE_RIGHT


def test_recover_position_after_dive_when_shot_streak_breaks() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 283)]))  # DIVE_RIGHT

    # bola desacelera bruscamente - quebra o criterio de velocidade do chute
    result = analyzer.analyze(_world(3, [_ball(249, 250)], [_goalkeeper(50, 260)]))  # dy=-23

    assert result.play_situation != PlaySituation.SHOT_DETECTED
    assert result.decision == GoalkeeperDecision.RECOVER_POSITION


def test_composes_the_five_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
    from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
    from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
    from worker.analyzers.play_situation import PlaySituationAnalyzer
    from worker.analyzers.shot import ShotAnalyzer

    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    assert isinstance(analyzer._play_situation_analyzer, PlaySituationAnalyzer)
    assert isinstance(analyzer._goalkeeper_position_analyzer, GoalkeeperPositionAnalyzer)
    assert isinstance(analyzer._goalkeeper_ball_alignment_analyzer, GoalkeeperBallAlignmentAnalyzer)
    assert isinstance(analyzer._ball_trajectory_analyzer, BallTrajectoryAnalyzer)
    assert isinstance(analyzer._shot_analyzer, ShotAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.goalkeeper_detected is True


def test_reset_clears_goalkeeper_motion_and_decision_state() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 283)]))  # DIVE_RIGHT

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.decision == GoalkeeperDecision.UNKNOWN  # primeira observacao de novo


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperDecisionAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "goalkeeper_decision"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
