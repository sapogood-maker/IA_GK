"""Testes de worker.analyzers.goalkeeper_performance_evaluation.
GoalkeeperPerformanceEvaluationAnalyzer - encerra a cadeia de avaliacao:
responde APENAS como foi o desempenho observado do goleiro, combinando
GoalkeeperDecisionEvaluationResult (W23) e PlayOutcomeResult (W24) via
o MESMO mecanismo de Rule Evaluation da W23. Nunca gera recomendacao,
nunca faz coaching."""
from __future__ import annotations

from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
from worker.analyzers.results import GoalkeeperPerformanceEvaluationResult
from worker.analyzers.rules import RuleOutcome
from worker.analyzers.types import GoalkeeperDecisionEvaluation, GoalkeeperPerformanceEvaluation, PlayOutcome
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
# validadas nas W23/W24 para os casos genuinamente alcancaveis via
# composicao real.
# ---------------------------------------------------------------------

def test_insufficient_information_when_nothing_is_visible() -> None:
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [], goals=[]))

    assert isinstance(result, GoalkeeperPerformanceEvaluationResult)
    assert result.performance == GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION
    assert "actors_and_geometry_available" in result.rules_failed


def test_unknown_on_first_observation() -> None:
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.performance == GoalkeeperPerformanceEvaluation.UNKNOWN
    assert "actors_and_geometry_available" in result.rules_passed
    assert "decisive_event_established" in result.rules_failed


def test_excellent_when_decision_compatible_and_outcome_is_save() -> None:
    """Goleiro parado durante um chute detectado (reacao compativel,
    PREPARE_DIVE) e a bola termina bem perto do goleiro - SAVE."""
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(110, 190)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(110, 190)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(110, 190)]))

    assert result.decision_evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE
    assert result.play_outcome == PlayOutcome.SAVE
    assert result.performance == GoalkeeperPerformanceEvaluation.EXCELLENT
    assert any("decision_fully_compatible" in rule for rule in result.rules_passed)
    assert any("outcome_is_save" in rule for rule in result.rules_passed)


def test_adequate_when_decision_compatible_and_outcome_is_goal() -> None:
    """Goleiro parado durante um chute detectado (reacao compativel),
    mas a bola termina dentro do gol - GOAL."""
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(200, 250)], [_goalkeeper(500, 450)]))
    analyzer.analyze(_world(1, [_ball(105, 250)], [_goalkeeper(500, 450)]))
    result = analyzer.analyze(_world(2, [_ball(15, 250)], [_goalkeeper(500, 450)]))

    assert result.decision_evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE
    assert result.play_outcome == PlayOutcome.GOAL
    assert result.performance == GoalkeeperPerformanceEvaluation.ADEQUATE


def test_explanations_are_present_for_every_rule() -> None:
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert len(result.rules_evaluated) == 8
    assert result.summary.startswith("performance=insufficient_information")
    assert "decision_evaluation=" in result.summary
    assert "play_outcome=" in result.summary
    assert "contributing_rules=" in result.summary


def test_composes_the_four_analyzers_internally_without_registry() -> None:
    from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
    from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
    from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
    from worker.analyzers.play_situation import PlaySituationAnalyzer

    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    assert isinstance(analyzer._play_situation_analyzer, PlaySituationAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_analyzer, GoalkeeperDecisionAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_evaluation_analyzer, GoalkeeperDecisionEvaluationAnalyzer)
    assert isinstance(analyzer._play_outcome_analyzer, PlayOutcomeAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.decision_evaluation is not None


def test_reset_clears_composed_analyzer_state() -> None:
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [], [_goalkeeper(50, 250)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.performance == GoalkeeperPerformanceEvaluation.UNKNOWN  # primeira observacao de novo


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperPerformanceEvaluationAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "goalkeeper_performance_evaluation"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0


# ---------------------------------------------------------------------
# Cruzamento completo (Decision Evaluation x Play Outcome) - testado
# diretamente na funcao de agregacao pura, mesmo padrao ja estabelecido
# na W23 (test_classify_incompatible...) para garantir cobertura
# exaustiva das 9 celulas da matriz deterministica, incluindo
# combinacoes dificeis de alcancar via composicao real completa.
# ---------------------------------------------------------------------

def _outcomes(decision_rule_id: str, outcome_rule_id: str) -> list[RuleOutcome]:
    return [
        RuleOutcome("actors_and_geometry_available", "...", True, "..."),
        RuleOutcome("decisive_event_established", "...", True, "..."),
        RuleOutcome("decision_fully_compatible", "...", decision_rule_id == "decision_fully_compatible", "..."),
        RuleOutcome(
            "decision_partially_compatible", "...", decision_rule_id == "decision_partially_compatible", "...",
        ),
        RuleOutcome("decision_incompatible", "...", decision_rule_id == "decision_incompatible", "..."),
        RuleOutcome("outcome_is_save", "...", outcome_rule_id == "outcome_is_save", "..."),
        RuleOutcome("outcome_is_neutral", "...", outcome_rule_id == "outcome_is_neutral", "..."),
        RuleOutcome("outcome_is_goal", "...", outcome_rule_id == "outcome_is_goal", "..."),
    ]


def test_classify_matrix_covers_all_nine_combinations() -> None:
    expected = {
        ("decision_fully_compatible", "outcome_is_save"): GoalkeeperPerformanceEvaluation.EXCELLENT,
        ("decision_fully_compatible", "outcome_is_neutral"): GoalkeeperPerformanceEvaluation.GOOD,
        ("decision_fully_compatible", "outcome_is_goal"): GoalkeeperPerformanceEvaluation.ADEQUATE,
        ("decision_partially_compatible", "outcome_is_save"): GoalkeeperPerformanceEvaluation.GOOD,
        ("decision_partially_compatible", "outcome_is_neutral"): GoalkeeperPerformanceEvaluation.ADEQUATE,
        ("decision_partially_compatible", "outcome_is_goal"): GoalkeeperPerformanceEvaluation.POOR,
        ("decision_incompatible", "outcome_is_save"): GoalkeeperPerformanceEvaluation.ADEQUATE,
        ("decision_incompatible", "outcome_is_neutral"): GoalkeeperPerformanceEvaluation.POOR,
        ("decision_incompatible", "outcome_is_goal"): GoalkeeperPerformanceEvaluation.CRITICAL,
    }

    for (decision_rule, outcome_rule), expected_performance in expected.items():
        outcomes = _outcomes(decision_rule, outcome_rule)
        performance = GoalkeeperPerformanceEvaluationAnalyzer._classify(outcomes)
        assert performance == expected_performance, f"{decision_rule} x {outcome_rule}"


def test_classify_insufficient_information_gate() -> None:
    outcomes = [RuleOutcome("actors_and_geometry_available", "...", False, "...")]
    assert (
        GoalkeeperPerformanceEvaluationAnalyzer._classify(outcomes)
        == GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION
    )


def test_classify_unknown_gate() -> None:
    outcomes = [
        RuleOutcome("actors_and_geometry_available", "...", True, "..."),
        RuleOutcome("decisive_event_established", "...", False, "..."),
    ]
    assert GoalkeeperPerformanceEvaluationAnalyzer._classify(outcomes) == GoalkeeperPerformanceEvaluation.UNKNOWN
