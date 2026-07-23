"""GoalkeeperPerformanceEvaluationAnalyzer: encerra a cadeia de
avaliação do sistema (Sprint W25) - responde APENAS "como foi o
desempenho OBSERVADO do goleiro nesta jogada?" (`GoalkeeperPerformanceEvaluation`,
fortemente tipado). NUNCA gera recomendação, NUNCA faz coaching, NUNCA
sugere melhoria - é a classificação FINAL da jogada, via o MESMO
mecanismo de Rule Evaluation da W23 (`worker.analyzers.rules`) - nenhum
mecanismo de regras novo foi criado, apenas novas regras específicas de
desempenho.

Cadeia completa desta arquitetura: Situação (W21, `PlaySituationAnalyzer`)
→ Decisão (W22, `GoalkeeperDecisionAnalyzer`) → Avaliação da Decisão
(W23, `GoalkeeperDecisionEvaluationAnalyzer`, compatibilidade
decisão-situação) → Resultado (W24, `PlayOutcomeAnalyzer`, resultado
observado da jogada) → Avaliação de Desempenho (W25, esta sprint,
combina Avaliação da Decisão + Resultado numa matriz determinística).
Este Analyzer NÃO observa nada novo - só COMBINA resultados já
produzidos, exclusivamente `GoalkeeperDecisionEvaluationResult.evaluation`
e `PlayOutcomeResult.outcome` (por instrução explícita desta sprint;
`PlaySituationAnalyzer`/`GoalkeeperDecisionAnalyzer` são compostos por
completude - fazem parte da lista de reuso explícita - mas contribuem
só como sinais adicionais de `confidence`, mesmo princípio já usado
desde a W20).

Segue o padrão de composição estabelecido nas W14-W24: instancia
`PlaySituationAnalyzer`/`GoalkeeperDecisionAnalyzer`/
`GoalkeeperDecisionEvaluationAnalyzer`/`PlayOutcomeAnalyzer`
internamente e chama `.analyze(football_world)` como função pura em
cada um - nenhum canal de comunicação especial entre Analyzers, nenhuma
mudança em `AnalyzerProcessor`/`ProcessorContext`. Sem `AnalyzerContext`
próprio - combinador puro, mesmo padrão de `PlaySituationAnalyzer` (W21)
e `GoalkeeperDecisionEvaluationAnalyzer` (W23)."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.base import Analyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperPerformanceEvaluationResult
from worker.analyzers.rules import Rule, RuleOutcome, evaluate_rules
from worker.analyzers.types import (
    AnalyzerName,
    AnalyzerVersion,
    GoalkeeperDecisionEvaluation,
    GoalkeeperPerformanceEvaluation,
    PlayOutcome,
)
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld

_NEUTRAL_OUTCOMES = (PlayOutcome.POST, PlayOutcome.BLOCKED, PlayOutcome.BALL_OUT, PlayOutcome.CROSSBAR)
_NON_DECISIVE_OUTCOMES = (PlayOutcome.UNKNOWN, PlayOutcome.LOST_TRACK, PlayOutcome.NO_SHOT_DETECTED)

# Matriz determinística 3x3: (eixo da decisão, eixo do resultado) -> avaliação final.
# Diagonal principal (decisao compativel + save -> EXCELLENT ... decisao
# incompativel + gol -> CRITICAL) reflete que a decisao (processo) pesa
# tanto quanto o resultado (sorte/resultado) - nunca julga só pelo
# resultado isolado, nunca só pela decisão isolada.
_PERFORMANCE_MATRIX: dict[tuple[str, str], GoalkeeperPerformanceEvaluation] = {
    ("compatible", "save"): GoalkeeperPerformanceEvaluation.EXCELLENT,
    ("compatible", "neutral"): GoalkeeperPerformanceEvaluation.GOOD,
    ("compatible", "goal"): GoalkeeperPerformanceEvaluation.ADEQUATE,
    ("partial", "save"): GoalkeeperPerformanceEvaluation.GOOD,
    ("partial", "neutral"): GoalkeeperPerformanceEvaluation.ADEQUATE,
    ("partial", "goal"): GoalkeeperPerformanceEvaluation.POOR,
    ("incompatible", "save"): GoalkeeperPerformanceEvaluation.ADEQUATE,
    ("incompatible", "neutral"): GoalkeeperPerformanceEvaluation.POOR,
    ("incompatible", "goal"): GoalkeeperPerformanceEvaluation.CRITICAL,
}


@dataclass(frozen=True)
class _PerformanceContext:
    """Entrada PURA das regras desta sprint - só os dois campos que a
    especificação autoriza usar, ecoados dos Analyzers compostos."""

    decision_evaluation: GoalkeeperDecisionEvaluation
    play_outcome: PlayOutcome


def _actors_and_geometry_available(ctx: _PerformanceContext) -> bool:
    """Sempre aplicável - sem informação básica de ambos os lados
    (decisão E resultado), nenhuma avaliação de desempenho é possível."""
    return (
        ctx.decision_evaluation != GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION
        and ctx.play_outcome != PlayOutcome.INSUFFICIENT_INFORMATION
    )


def _decisive_event_established(ctx: _PerformanceContext) -> bool | None:
    """Só aplicável quando a regra anterior passou - verifica se há um
    evento decisivo genuíno para avaliar (decisão estabelecida E
    resultado decisivo, não apenas 'ainda observando')."""
    if not _actors_and_geometry_available(ctx):
        return None
    return (
        ctx.decision_evaluation != GoalkeeperDecisionEvaluation.UNKNOWN
        and ctx.play_outcome not in _NON_DECISIVE_OUTCOMES
    )


def _is_evaluable(ctx: _PerformanceContext) -> bool:
    return _actors_and_geometry_available(ctx) and _decisive_event_established(ctx) is True


def _decision_fully_compatible(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.decision_evaluation == GoalkeeperDecisionEvaluation.COMPATIBLE


def _decision_partially_compatible(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.decision_evaluation == GoalkeeperDecisionEvaluation.PARTIALLY_COMPATIBLE


def _decision_incompatible(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.decision_evaluation == GoalkeeperDecisionEvaluation.INCOMPATIBLE


def _outcome_is_save(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.play_outcome == PlayOutcome.SAVE


def _outcome_is_neutral(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.play_outcome in _NEUTRAL_OUTCOMES


def _outcome_is_goal(ctx: _PerformanceContext) -> bool | None:
    if not _is_evaluable(ctx):
        return None
    return ctx.play_outcome == PlayOutcome.GOAL


_RULES: list[Rule[_PerformanceContext]] = [
    Rule(
        "actors_and_geometry_available",
        "Avaliacao de decisao e resultado da jogada devem estar disponiveis (nao INSUFFICIENT_INFORMATION)",
        _actors_and_geometry_available,
    ),
    Rule(
        "decisive_event_established",
        "Deve haver um evento decisivo estabelecido (decisao conhecida e resultado decisivo)",
        _decisive_event_established,
    ),
    Rule("decision_fully_compatible", "A decisao do goleiro foi totalmente compativel com a situacao", _decision_fully_compatible),
    Rule(
        "decision_partially_compatible", "A decisao do goleiro foi parcialmente compativel com a situacao",
        _decision_partially_compatible,
    ),
    Rule("decision_incompatible", "A decisao do goleiro foi incompativel com a situacao", _decision_incompatible),
    Rule("outcome_is_save", "O resultado observado da jogada foi uma defesa", _outcome_is_save),
    Rule(
        "outcome_is_neutral", "O resultado observado nao foi claramente gol nem defesa (poste/travessao/bloqueio/bola fora)",
        _outcome_is_neutral,
    ),
    Rule("outcome_is_goal", "O resultado observado da jogada foi um gol", _outcome_is_goal),
]


class GoalkeeperPerformanceEvaluationAnalyzer(Analyzer):
    """Responde apenas: "como foi o desempenho observado do goleiro
    nesta jogada?" - classificação determinística e fortemente tipada
    (`GoalkeeperPerformanceEvaluation`), nunca uma recomendação ou
    coaching."""

    name = "goalkeeper_performance_evaluation"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._play_situation_analyzer = PlaySituationAnalyzer(settings)
        self._goalkeeper_decision_analyzer = GoalkeeperDecisionAnalyzer(settings)
        self._goalkeeper_decision_evaluation_analyzer = GoalkeeperDecisionEvaluationAnalyzer(settings)
        self._play_outcome_analyzer = PlayOutcomeAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        play_situation = self._play_situation_analyzer.analyze(football_world)
        decision_result = self._goalkeeper_decision_analyzer.analyze(football_world)
        decision_evaluation_result = self._goalkeeper_decision_evaluation_analyzer.analyze(football_world)
        outcome_result = self._play_outcome_analyzer.analyze(football_world)

        context = _PerformanceContext(
            decision_evaluation=decision_evaluation_result.evaluation,
            play_outcome=outcome_result.outcome,
        )
        outcomes = evaluate_rules(_RULES, context)
        performance = self._classify(outcomes)

        rules_evaluated = [outcome.rule_id for outcome in outcomes]
        rules_passed = [outcome.rule_id for outcome in outcomes if outcome.passed is True]
        rules_failed = [outcome.rule_id for outcome in outcomes if outcome.passed is False]
        summary = self._build_summary(
            performance, decision_evaluation_result.evaluation, outcome_result.outcome, rules_passed,
        )

        confidence = None
        signals = [
            play_situation.confidence, decision_result.confidence,
            decision_evaluation_result.confidence, outcome_result.confidence,
        ]
        if all(signal is not None for signal in signals):
            confidence = min(signals)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperPerformanceEvaluationResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            performance=performance,
            decision_evaluation=decision_evaluation_result.evaluation,
            play_outcome=outcome_result.outcome,
            rules_evaluated=rules_evaluated,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            summary=summary,
            confidence=confidence,
        )

    @staticmethod
    def _classify(outcomes: list[RuleOutcome]) -> GoalkeeperPerformanceEvaluation:
        """Agrega os `RuleOutcome`s num veredito único - nunca lê nada
        além dos próprios resultados das regras.

        `actors_and_geometry_available=False` -> INSUFFICIENT_INFORMATION
        (nem a decisão nem o resultado estão disponíveis para avaliar).
        `decisive_event_established=False` (mas o gate anterior passou)
        -> UNKNOWN (histórico insuficiente ou nenhum evento decisivo
        ainda - jogada ainda em andamento, sem chute/rastreamento
        conclusivo). Caso contrário, localiza qual dos três eixos de
        decisão (`compatible`/`partial`/`incompatible`) e qual dos três
        eixos de resultado (`save`/`neutral`/`goal`) foram satisfeitos, e
        consulta a matriz determinística `_PERFORMANCE_MATRIX` - nunca
        uma heurística oculta, sempre rastreável até exatamente duas
        regras (uma de cada eixo)."""
        by_id = {outcome.rule_id: outcome.passed for outcome in outcomes}

        if by_id.get("actors_and_geometry_available") is False:
            return GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION
        if by_id.get("decisive_event_established") is False:
            return GoalkeeperPerformanceEvaluation.UNKNOWN

        if by_id.get("decision_fully_compatible"):
            decision_axis = "compatible"
        elif by_id.get("decision_partially_compatible"):
            decision_axis = "partial"
        else:
            decision_axis = "incompatible"

        if by_id.get("outcome_is_save"):
            outcome_axis = "save"
        elif by_id.get("outcome_is_neutral"):
            outcome_axis = "neutral"
        else:
            outcome_axis = "goal"

        return _PERFORMANCE_MATRIX[(decision_axis, outcome_axis)]

    @staticmethod
    def _build_summary(
        performance: GoalkeeperPerformanceEvaluation, decision_evaluation: GoalkeeperDecisionEvaluation,
        play_outcome: PlayOutcome, rules_passed: list[str],
    ) -> str:
        """String ESTRUTURADA, não linguagem natural (por instrução
        explícita desta sprint) - suficiente para auditoria sem gerar
        prosa/coaching."""
        contributing = ",".join(rules_passed) if rules_passed else "none"
        return (
            f"performance={performance.value}; decision_evaluation={decision_evaluation.value}; "
            f"play_outcome={play_outcome.value}; contributing_rules={contributing}"
        )

    def reset(self) -> None:
        """Delega `reset()` aos quatro Analyzers compostos - dois deles
        (`GoalkeeperDecisionAnalyzer`/`PlayOutcomeAnalyzer`) são
        genuinamente STATEFUL; os demais são combinadores puros,
        chamados por completude (mesmo princípio já aplicado por
        `ShotAnalyzer.reset()`, W19). Este Analyzer não tem
        `AnalyzerContext` próprio."""
        self._play_situation_analyzer.reset()
        self._goalkeeper_decision_analyzer.reset()
        self._goalkeeper_decision_evaluation_analyzer.reset()
        self._play_outcome_analyzer.reset()
