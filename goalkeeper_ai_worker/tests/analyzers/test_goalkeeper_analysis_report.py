"""Testes de worker.analyzers.goalkeeper_analysis_report.
GoalkeeperAnalysisReportAnalyzer - encerra oficialmente o MVP
arquitetural: agrega, sem recalcular nada, os seis resultados
cognitivos ja produzidos (PlaySituationResult/GoalkeeperDecisionResult/
GoalkeeperDecisionEvaluationResult/PlayOutcomeResult/
GoalkeeperPerformanceEvaluationResult/GoalkeeperCoachingResult) num
unico GoalkeeperAnalysisReport - o CONTRATO OFICIAL de saida do Worker."""
from __future__ import annotations

from worker.analyzers.goalkeeper_analysis_report import GoalkeeperAnalysisReportAnalyzer
from worker.analyzers.results import GoalkeeperAnalysisReport
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

_SIX_SUB_RESULT_KEYS = (
    "play_situation", "goalkeeper_decision", "goalkeeper_decision_evaluation",
    "play_outcome", "goalkeeper_performance_evaluation", "goalkeeper_coaching",
)


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
# Construcao completa do relatorio - cenario real composto (sem mock),
# reaproveitando a sequencia SAVE/EXCELLENT ja validada nas W25/W26.
# ---------------------------------------------------------------------

def test_report_construction_with_full_information() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(110, 190)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(110, 190)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(110, 190)]))

    assert isinstance(result, GoalkeeperAnalysisReport)
    assert result.performance_evaluation.performance.value == "excellent"
    assert result.coaching.coaching.value == "no_feedback"
    assert result.play_outcome.outcome.value == "save"
    assert result.decision_evaluation.evaluation.value == "compatible"
    assert result.confidence_summary["overall"] is not None
    assert set(result.artifacts.keys()) == set(_SIX_SUB_RESULT_KEYS)
    assert result.analysis_version == "1.0.0"
    assert result.worker_version
    assert result.generated_at  # timestamp real, nao vazio


# ---------------------------------------------------------------------
# Ausencia parcial de informacoes - nada visivel: o relatorio ainda deve
# ser construido com sucesso, cada sub-resultado honestamente vazio.
# ---------------------------------------------------------------------

def test_report_construction_with_no_information_available() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], [], goals=[]))

    assert result.performance_evaluation.performance.value == "insufficient_information"
    assert result.coaching.coaching.value == "insufficient_information"
    assert result.play_outcome.outcome.value == "insufficient_information"
    assert result.decision_evaluation.evaluation.value == "insufficient_information"
    # Nenhuma confidence disponivel neste cenario -> overall honestamente None
    assert result.confidence_summary["overall"] is None
    assert set(result.artifacts.keys()) == set(_SIX_SUB_RESULT_KEYS)


def test_report_construction_on_first_observation() -> None:
    """So bola/goleiro detectados, sem historico - UNKNOWN em cascata,
    nunca um crash por falta de dado."""
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))

    assert result.performance_evaluation.performance.value == "unknown"
    assert result.coaching.coaching.value == "unknown"


# ---------------------------------------------------------------------
# Preservacao integral da Explainability - nada produzido pelos seis
# Analyzers compostos pode ser removido/reconstruido pelo relatorio.
# ---------------------------------------------------------------------

def test_explainability_is_preserved_integrally_for_every_sub_result() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    # decision_evaluation, performance_evaluation e coaching expoem
    # rules_evaluated/rules_passed/rules_failed - nada disso pode ficar
    # vazio "por reconstrucao" no relatorio, tem que vir do sub-resultado.
    assert len(result.decision_evaluation.rules_evaluated) == 6
    assert len(result.performance_evaluation.rules_evaluated) == 8
    assert len(result.coaching.rules_evaluated) == 8
    assert result.play_outcome.supporting_evidence  # lista simples, nao vazia

    payload = result.to_dict()
    assert payload["decision_evaluation"]["rules_evaluated"] == result.decision_evaluation.rules_evaluated
    assert payload["performance_evaluation"]["rules_failed"] == result.performance_evaluation.rules_failed
    assert payload["coaching"]["summary"] == result.coaching.summary
    assert payload["play_outcome"]["supporting_evidence"] == result.play_outcome.supporting_evidence
    # O espelho em "artifacts" tem que ser byte-a-byte identico aos campos tipados
    assert payload["artifacts"]["goalkeeper_coaching"] == payload["coaching"]
    assert payload["artifacts"]["goalkeeper_performance_evaluation"] == payload["performance_evaluation"]
    assert payload["artifacts"]["goalkeeper_decision_evaluation"] == payload["decision_evaluation"]


def test_confidence_summary_consolidates_without_recalculating() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(250.0, 63.4)], [_goalkeeper(110, 190)]))
    analyzer.analyze(_world(1, [_ball(175.0, 121.7)], [_goalkeeper(110, 190)]))
    result = analyzer.analyze(_world(2, [_ball(100, 180)], [_goalkeeper(110, 190)]))

    assert result.confidence_summary["play_situation"] == result.play_situation.confidence
    assert result.confidence_summary["goalkeeper_decision"] == result.goalkeeper_decision.confidence
    assert result.confidence_summary["goalkeeper_decision_evaluation"] == result.decision_evaluation.confidence
    assert result.confidence_summary["play_outcome"] == result.play_outcome.confidence
    assert (
        result.confidence_summary["goalkeeper_performance_evaluation"]
        == result.performance_evaluation.confidence
    )
    assert result.confidence_summary["goalkeeper_coaching"] == result.coaching.confidence
    signals = [v for k, v in result.confidence_summary.items() if k != "overall"]
    assert result.confidence_summary["overall"] == min(signals)


# ---------------------------------------------------------------------
# Composicao/reset/metadata
# ---------------------------------------------------------------------

def test_composes_the_six_analyzers_internally_without_registry() -> None:
    from worker.analyzers.goalkeeper_coaching import GoalkeeperCoachingAnalyzer
    from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
    from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
    from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
    from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
    from worker.analyzers.play_situation import PlaySituationAnalyzer

    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    assert isinstance(analyzer._play_situation_analyzer, PlaySituationAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_analyzer, GoalkeeperDecisionAnalyzer)
    assert isinstance(analyzer._goalkeeper_decision_evaluation_analyzer, GoalkeeperDecisionEvaluationAnalyzer)
    assert isinstance(analyzer._play_outcome_analyzer, PlayOutcomeAnalyzer)
    assert isinstance(
        analyzer._goalkeeper_performance_evaluation_analyzer, GoalkeeperPerformanceEvaluationAnalyzer,
    )
    assert isinstance(analyzer._goalkeeper_coaching_analyzer, GoalkeeperCoachingAnalyzer)

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.decision_evaluation is not None


def test_reset_clears_composed_analyzer_state() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(1, [_ball(295, 250)], [_goalkeeper(50, 250)]))
    analyzer.analyze(_world(2, [], [_goalkeeper(50, 250)]))

    analyzer.reset()

    result = analyzer.analyze(_world(0, [_ball(300, 250)], [_goalkeeper(50, 250)]))
    assert result.performance_evaluation.performance.value == "unknown"  # primeira observacao de novo


def test_metadata_identifies_the_analyzer() -> None:
    analyzer = GoalkeeperAnalysisReportAnalyzer(get_settings())
    result = analyzer.analyze(_world(0, [], []))

    assert result.metadata.analyzer_name == "goalkeeper_analysis_report"
    assert result.metadata.analyzer_version == "1.0.0"
    assert result.metadata.processing_time_ms >= 0.0
