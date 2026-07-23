"""Testes de worker.analyzers.goalkeeper_coaching.
GoalkeeperCoachingAnalyzer - primeiro Analyzer de COACHING: responde
APENAS qual orientacao tecnica pode ser extraida da jogada, combinando
GoalkeeperPerformanceEvaluationResult (W25), GoalkeeperDecisionEvaluationResult
(W23, via rules_passed/rules_failed), GoalkeeperDecisionResult (W22) e
PlayOutcomeResult (W24) via o MESMO mecanismo de Rule Evaluation da W23.
Nunca gera linguagem natural, nunca produz relatorio final."""
from __future__ import annotations

from worker.analyzers.goalkeeper_coaching import GoalkeeperCoachingAnalyzer
from worker.analyzers.results import GoalkeeperCoachingResult
from worker.analyzers.rules import RuleOutcome
from worker.analyzers.types import GoalkeeperCoaching, GoalkeeperPerformanceEvaluation
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


# ---------------------------------------------------------------------
# Cenarios reais compostos (sem mock) - reaproveitam sequencias ja
# validadas nas W23/W24/W25 para os casos genuinamente alcancaveis via
# composicao real completa.
# ---------------------------------------------------------------------

def test_insufficient_information_when_nothing_is_visible() -> None:
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [], goals=[]))

    assert isinstance(result, GoalkeeperCoachingResult)
    assert result.coaching == GoalkeeperCoaching.INSUFFICIENT_INFORMATION
    assert "evaluation_available" in result.rules_failed


def test_unknown_on_first_observation() -> None:
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.coaching == GoalkeeperCoaching.UNKNOWN
    assert "evaluation_available" in result.rules_passed
    assert "decisive_performance_established" in result.rules_failed


def test_no_feedback_when_performance_is_excellent() -> None:
    """Goleiro parado durante um chute detectado (reacao compativel,
    PREPARE_DIVE) e a bola termina bem perto do goleiro - SAVE ->
    performance EXCELLENT (W25) -> coaching de REFORCO, NO_FEEDBACK."""
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(110, 190)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(110, 190)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(110, 190)]))

    assert result.performance == GoalkeeperPerformanceEvaluation.EXCELLENT
    assert result.coaching == GoalkeeperCoaching.NO_FEEDBACK
    assert "performance_was_reinforcement" in result.rules_passed


def test_improve_positioning_when_compatible_decision_still_concedes_a_goal() -> None:
    """Goleiro parado durante um chute detectado (reacao compativel,
    PREPARE_DIVE), mas a bola termina dentro do gol - GOAL -> performance
    ADEQUATE (W25). Como a decisao ja foi uma reacao ATIVA
    (PREPARE_DIVE esta em _ACTIVE_SHOT_RESPONSES), nenhuma regra
    especifica de coaching se aplica - cai no residual IMPROVE_POSITIONING."""
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(200, 250)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(105, 250)], [_goalkeeper(500, 450)]))
    result = analyzer.analyze(_world(2, [_ball(15, 250)], [_goalkeeper(500, 450)]))

    assert result.performance == GoalkeeperPerformanceEvaluation.ADEQUATE
    assert result.outcome.value == "goal"
    assert result.coaching == GoalkeeperCoaching.IMPROVE_POSITIONING


def test_explanations_are_present_for_every_rule() -> None:
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert len(result.rules_evaluated) == 8
    assert result.summary.startswith("coaching=insufficient_information")
    assert "performance=" in result.summary
    assert "decision=" in result.summary
    assert "outcome=" in result.summary
    assert "contributing_rules=" in result.summary


def test_composes_the_four_analyzers_internally_without_registry() -> None:
    from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
    from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
    from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
    from worker.analyzers.play_outcome import PlayOutcomeAnalyzer

    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    assert isinstance(analyzer._performance_analyzer, GoalkeeperPerformanceEvaluationAnalyzer)
    assert isinstance(analyzer._decision_evaluation_analyzer, GoalkeeperDecisionEvaluationAnalyzer)
    assert isinstance(analyzer._play_outcome_analyzer, PlayOutcomeAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_analyzer, GoalkeeperDecisionAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.decision_evaluation is not None


def test_reset_clears_composed_analyzer_state() -> None:
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [], [_goalkeeper(50, 250)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.coaching == GoalkeeperCoaching.UNKNOWN  # primeira observacao de novo


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperCoachingAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "goalkeeper_coaching"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0


# ---------------------------------------------------------------------
# Cobertura exaustiva de _classify() - mesmo padrao ja estabelecido nas
# W23/W25 (test_classify_incompatible.../test_classify_matrix_covers_all_nine_combinations)
# para garantir cobertura de todas as dez orientacoes de GoalkeeperCoaching,
# incluindo combinacoes dificeis (ou impossiveis, ver ATTACK_BALL abaixo)
# de alcancar via composicao real completa.
# ---------------------------------------------------------------------

def _all_false(*true_ids: str) -> list[RuleOutcome]:
    ids = [
        "evaluation_available", "decisive_performance_established", "performance_was_reinforcement",
        "conceded_goal_without_active_response", "committed_without_shot", "reacted_passively_to_shot",
        "dived_wrong_direction", "recovery_was_insufficient",
    ]
    return [RuleOutcome(rule_id, "...", rule_id in true_ids, "...") for rule_id in ids]


def test_classify_insufficient_information_gate() -> None:
    outcomes = [RuleOutcome("evaluation_available", "...", False, "...")]
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION)
    assert coaching == GoalkeeperCoaching.INSUFFICIENT_INFORMATION


def test_classify_unknown_gate() -> None:
    outcomes = [
        RuleOutcome("evaluation_available", "...", True, "..."),
        RuleOutcome("decisive_performance_established", "...", False, "..."),
    ]
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.UNKNOWN)
    assert coaching == GoalkeeperCoaching.UNKNOWN


def test_classify_no_feedback_when_performance_is_excellent() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "performance_was_reinforcement")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.EXCELLENT)
    assert coaching == GoalkeeperCoaching.NO_FEEDBACK


def test_classify_keep_position_when_performance_is_good() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "performance_was_reinforcement")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.GOOD)
    assert coaching == GoalkeeperCoaching.KEEP_POSITION


def test_classify_attack_ball_when_goal_conceded_without_active_response() -> None:
    """Estruturalmente dificil de alcancar via composicao real completa:
    `PlayOutcome.GOAL` so e produzido quando `shot_detected=True` (W24),
    e `GoalkeeperDecisionAnalyzer` (W22) SEMPRE classifica
    `PREPARE_DIVE`/`DIVE_LEFT`/`DIVE_RIGHT` (uma resposta ativa) quando
    `shot_detected=True` - por construcao, `decision` nunca fica fora de
    `_ACTIVE_SHOT_RESPONSES` no mesmo frame em que `outcome=GOAL`. Testado
    diretamente na agregacao pura, mesmo padrao do Risco 38 (W23)."""
    outcomes = _all_false(
        "evaluation_available", "decisive_performance_established", "conceded_goal_without_active_response",
    )
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.CRITICAL)
    assert coaching == GoalkeeperCoaching.ATTACK_BALL


def test_classify_move_later_when_committed_without_shot() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "committed_without_shot")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.POOR)
    assert coaching == GoalkeeperCoaching.MOVE_LATER


def test_classify_move_earlier_when_reacted_passively_to_shot() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "reacted_passively_to_shot")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.POOR)
    assert coaching == GoalkeeperCoaching.MOVE_EARLIER


def test_classify_stay_patient_when_dived_wrong_direction() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "dived_wrong_direction")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.POOR)
    assert coaching == GoalkeeperCoaching.STAY_PATIENT


def test_classify_recover_faster_when_recovery_was_insufficient() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established", "recovery_was_insufficient")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.POOR)
    assert coaching == GoalkeeperCoaching.RECOVER_FASTER


def test_classify_improve_positioning_fallback_when_no_specific_rule_applies() -> None:
    outcomes = _all_false("evaluation_available", "decisive_performance_established")
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.ADEQUATE)
    assert coaching == GoalkeeperCoaching.IMPROVE_POSITIONING


def test_classify_priority_attack_ball_wins_over_move_earlier() -> None:
    """Documenta o desempate: quando mais de uma regra especifica e
    satisfeita ao mesmo tempo (ex.: reacao passiva a um chute que
    termina em gol), a mais severa/concreta (gol sofrido) prevalece -
    desempate deterministico, nao uma ambiguidade real."""
    outcomes = _all_false(
        "evaluation_available", "decisive_performance_established",
        "conceded_goal_without_active_response", "reacted_passively_to_shot",
    )
    coaching = GoalkeeperCoachingAnalyzer._classify(outcomes, GoalkeeperPerformanceEvaluation.CRITICAL)
    assert coaching == GoalkeeperCoaching.ATTACK_BALL
