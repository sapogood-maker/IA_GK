"""Testes de worker.analyzers.goalkeeper_decision_evaluation.
GoalkeeperDecisionEvaluationAnalyzer - primeiro Analyzer de AVALIACAO:
responde apenas se a decisao observada do goleiro foi compativel com a
situacao observada, via um mecanismo explicito de Rule Evaluation.
Nunca avalia o resultado da jogada, nunca julga desempenho."""
from __future__ import annotations

from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.results import GoalkeeperDecisionEvaluationResult
from worker.analyzers.rules import RuleOutcome
from worker.analyzers.types import GoalkeeperDecisionEvaluation, PlaySituation
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
    frame_index: int, balls: list[Ball], goalkeepers: list[Goalkeeper] | None = None,
) -> FootballWorld:
    return FootballWorld(
        frame_index=frame_index, balls=balls, goalkeepers=goalkeepers or [], goals=[_goal()], field=_field(),
    )


def test_insufficient_information_when_ball_not_visible() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [_goalkeeper(50, 250)]))

    assert isinstance(result, GoalkeeperDecisionEvaluationResult)
    assert result.evaluation == GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION
    assert "actors_visible" in result.rules_failed
    assert result.confidence is None


def test_insufficient_information_when_goalkeeper_not_visible() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], []))

    assert result.evaluation == GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION
    assert "actors_visible" in result.rules_failed


def test_unknown_on_first_observation() -> None:
    """Atores visiveis, mas o goleiro ainda nao tem historico suficiente
    (primeira observacao, W22) - distinto de INSUFFICIENT_INFORMATION."""
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.evaluation == GoalkeeperDecisionEvaluation.UNKNOWN
    assert "actors_visible" in result.rules_passed
    assert "decision_established" in result.rules_failed


def test_compatible_when_no_content_rule_is_applicable() -> None:
    """Bola e goleiro parados - nenhuma regra de conteudo se aplica
    (nada a contradizer) - COMPATIBLE por padrao."""
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(1, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE
    assert "shot_prompts_active_response" not in result.rules_passed
    assert "shot_prompts_active_response" not in result.rules_failed
    assert "shot_prompts_active_response" in result.rules_evaluated  # avaliada, so nao aplicavel


def test_compatible_dive_direction_matches_ball_direction() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 245)], [_goalkeeper(50, 250)]))  # 1o frame qualificante
    result = analyzer.analyze(_world(2, [_ball(250, 240)], [_goalkeeper(50, 220)]))  # shot + dive esquerda

    assert result.play_situation == PlaySituation.SHOT_DETECTED
    assert result.evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE
    assert "dive_direction_matches_ball_direction" in result.rules_passed
    assert result.confidence is not None


def test_partially_compatible_dive_direction_mismatches_ball_direction() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 245)], [_goalkeeper(50, 250)]))
    # bola vai para a esquerda (dy negativo), goleiro mergulha para a direita (dy positivo)
    result = analyzer.analyze(_world(2, [_ball(250, 240)], [_goalkeeper(50, 280)]))

    assert result.evaluation == GoalkeeperDecisionEvaluation.PARTIALLY_COMPATIBLE
    assert "dive_direction_matches_ball_direction" in result.rules_failed
    assert "shot_prompts_active_response" in result.rules_passed


def test_dive_direction_rule_not_applicable_when_ball_lateral_signal_is_weak() -> None:
    """Bola se move em linha reta (sem componente lateral) - o sinal e
    fraco demais para julgar a direcao do mergulho, entao a regra fica
    NAO APLICAVEL em vez de forcar um veredito sobre ruido."""
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 250)], [_goalkeeper(50, 250)]))
    result = analyzer.analyze(_world(2, [_ball(250, 250)], [_goalkeeper(50, 220)]))  # ball dy=0, dive esquerda

    assert result.evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE
    assert "dive_direction_matches_ball_direction" not in result.rules_passed
    assert "dive_direction_matches_ball_direction" not in result.rules_failed
    assert "dive_direction_matches_ball_direction" in result.rules_evaluated


def test_rules_evaluated_always_lists_all_six_rules() -> None:
    """Explicabilidade: todas as regras sao sempre reportadas, mesmo
    quando nao aplicaveis - nenhuma decisao e tomada silenciosamente."""
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert len(result.rules_evaluated) == 6
    assert len(result.explanations) == 6
    assert "actors_visible" in result.rules_evaluated


def test_classify_incompatible_when_all_applicable_content_rules_fail() -> None:
    """Cenario sintetico - nao alcancavel via composicao real com o
    conjunto de regras atual (a maioria audita garantias ja asseguradas
    pelo proprio GoalkeeperDecisionAnalyzer, W22), mas a logica de
    agregacao precisa estar correta para o caso em que TODAS as regras
    de conteudo aplicaveis falham."""
    outcomes = [
        RuleOutcome("actors_visible", "...", True, "..."),
        RuleOutcome("decision_established", "...", True, "..."),
        RuleOutcome("shot_prompts_active_response", "...", False, "..."),
    ]

    evaluation = GoalkeeperDecisionEvaluationAnalyzer._classify(outcomes)
    assert evaluation == GoalkeeperDecisionEvaluation.INCOMPATIBLE


def test_composes_the_six_analyzers_internally_without_registry() -> None:
    from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
    from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
    from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
    from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
    from worker.analyzers.play_situation import PlaySituationAnalyzer
    from worker.analyzers.shot import ShotAnalyzer

    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    assert isinstance(analyzer._play_situation_analyzer, PlaySituationAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_analyzer, GoalkeeperDecisionAnalyzer)
    assert isinstance(analyzer._goalkeeper_position_analyzer, GoalkeeperPositionAnalyzer)
    assert isinstance(analyzer._goalkeeper_ball_alignment_analyzer, GoalkeeperBallAlignmentAnalyzer)
    assert isinstance(analyzer._ball_trajectory_analyzer, BallTrajectoryAnalyzer)
    assert isinstance(analyzer._shot_analyzer, ShotAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.goalkeeper_decision is not None


def test_reset_clears_composed_analyzer_state() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(275, 245)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [_ball(250, 240)], [_goalkeeper(50, 220)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.evaluation == GoalkeeperDecisionEvaluation.UNKNOWN  # primeira observacao de novo


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperDecisionEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "goalkeeper_decision_evaluation"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
