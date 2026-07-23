"""Testes de worker.analyzers.play_outcome.PlayOutcomeAnalyzer - encerra
a cadeia de observacao: responde APENAS qual foi o resultado observado
da jogada. Nunca avalia o goleiro, nunca atribui nota, nunca julga a
qualidade da decisao."""
from __future__ import annotations

from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.results import PlayOutcomeResult
from worker.analyzers.types import PlayOutcome
from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.direction import Direction
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.geometry.coordinate import Coordinate
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
    frame_index: int, balls: list[Ball], goalkeepers: list[Goalkeeper] | None = None, goals=None,
) -> FootballWorld:
    return FootballWorld(
        frame_index=frame_index, balls=balls, goalkeepers=goalkeepers or [],
        goals=[_goal()] if goals is None else goals, field=_field(),
    )


def test_insufficient_information_when_goal_not_visible() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)], goals=[]))

    assert isinstance(result, PlayOutcomeResult)
    assert result.outcome == PlayOutcome.INSUFFICIENT_INFORMATION
    assert result.goal_visible is False


def test_insufficient_information_when_ball_never_appeared() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [_goalkeeper(50, 250)]))

    assert result.outcome == PlayOutcome.INSUFFICIENT_INFORMATION
    assert result.ball_detected is False
    assert result.ball_last_position is None


def test_unknown_on_first_observation() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.outcome == PlayOutcome.UNKNOWN
    assert result.ball_last_position == Coordinate(x=300, y=250)


def test_no_shot_detected_when_ball_moves_slowly() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))  # speed=5

    assert result.shot_detected is False
    assert result.outcome == PlayOutcome.NO_SHOT_DETECTED


def test_lost_track_when_ball_disappears_after_being_tracked() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))  # trajectoria estabelecida

    result = analyzer.analyze(_world(2, [], [_goalkeeper(50, 250)]))  # bola some

    assert result.outcome == PlayOutcome.LOST_TRACK
    assert result.ball_detected is False
    assert result.ball_last_position == Coordinate(x=295, y=250)  # ultima posicao conhecida preservada


def test_goal_when_ball_lands_inside_a_goal_zone() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(200, 250)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(105, 250)], [_goalkeeper(500, 450)]))  # 1o frame qualificante
    result = analyzer.analyze(_world(2, [_ball(15, 250)], [_goalkeeper(500, 450)]))  # shot_detected=True

    assert result.shot_detected is True
    assert result.outcome == PlayOutcome.GOAL
    assert any("zona do gol" in evidence for evidence in result.supporting_evidence)
    assert result.confidence is not None


def test_post_when_ball_lands_near_a_post_outside_the_goal_frame() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(-59.6, 68.4)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(-32.3, 109.0)], [_goalkeeper(500, 450)]))
    result = analyzer.analyze(_world(2, [_ball(-5, 200)], [_goalkeeper(500, 450)]))  # shot_detected=True

    assert result.outcome == PlayOutcome.POST
    assert any("left_post" in evidence or "right_post" in evidence for evidence in result.supporting_evidence)


def test_save_when_goalkeeper_close_to_the_ball_last_position() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(110, 190)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(110, 190)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(110, 190)]))  # shot_detected=True

    assert result.outcome == PlayOutcome.SAVE
    assert any("goleiro" in evidence for evidence in result.supporting_evidence)


def test_blocked_when_trajectory_shows_a_direction_change_and_no_goalkeeper_nearby() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(50.0, 68.4)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(250.0, 63.4)], [_goalkeeper(500, 450)]))  # virada abrupta
    analyzer.analyze(_world(2, [_ball(175.0, 121.7)], [_goalkeeper(500, 450)]))  # 1o frame qualificante
    result = analyzer.analyze(_world(3, [_ball(100, 180)], [_goalkeeper(500, 450)]))  # shot_detected=True

    assert result.outcome == PlayOutcome.BLOCKED
    assert any("mudanca" in evidence for evidence in result.supporting_evidence)


def test_ball_out_when_ball_lands_outside_the_field_region() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(667.8, -99.1)]))
    analyzer.analyze(_world(1, [_ball(583.9, -54.5)]))
    result = analyzer.analyze(_world(2, [_ball(500, -10)]))  # shot_detected=True, fora do campo

    assert result.outcome == PlayOutcome.BALL_OUT


def test_unknown_when_shot_detected_but_no_geometric_condition_matches() -> None:
    """Chute detectado, bola ainda 'em voo' - nenhuma zona/poste/goleiro/
    desvio/fora-de-campo bate ainda."""
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(500, 450)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(500, 450)]))  # goleiro longe

    assert result.shot_detected is True
    assert result.outcome == PlayOutcome.UNKNOWN


def test_composes_the_five_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
    from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
    from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
    from worker.analyzers.play_situation import PlaySituationAnalyzer
    from worker.analyzers.shot import ShotAnalyzer

    analyzer = PlayOutcomeAnalyzer(get_settings())
    assert isinstance(analyzer._play_situation_analyzer, PlaySituationAnalyzer)
    assert isinstance(analyzer._shot_analyzer, ShotAnalyzer)
    assert isinstance(analyzer._ball_trajectory_analyzer, BallTrajectoryAnalyzer)
    assert isinstance(analyzer._goal_geometry_analyzer, GoalGeometryAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_analyzer, GoalkeeperDecisionAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.ball_detected is True


def test_reset_clears_tracking_state_between_jobs() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [], [_goalkeeper(50, 250)]))  # LOST_TRACK

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.outcome == PlayOutcome.UNKNOWN  # primeira observacao de novo, nao LOST_TRACK
    assert result.ball_last_position == Coordinate(x=300, y=250)


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = PlayOutcomeAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "play_outcome"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
