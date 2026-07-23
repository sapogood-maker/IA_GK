"""GoalkeeperCoachingAnalyzer: primeiro Analyzer de COACHING (Sprint
W26) - responde APENAS "qual orientação técnica pode ser extraída desta
jogada?" (`GoalkeeperCoaching`, fortemente tipado). NUNCA gera
linguagem natural, NUNCA produz relatório final, NUNCA sugere um plano
de treino - é uma classificação determinística, via o MESMO mecanismo
de Rule Evaluation da W23 (`worker.analyzers.rules` - nenhum mecanismo
de regras novo foi criado, apenas novas regras específicas de
Coaching).

Cadeia completa desta arquitetura: Situação (W21) → Decisão (W22) →
Avaliação da Decisão (W23) → Resultado (W24) → Avaliação de Desempenho
(W25) → Coaching (W26, esta sprint, primeira orientação técnica). Este
Analyzer NÃO observa nada novo, NÃO calcula nenhuma métrica nova - só
INTERPRETA resultados já produzidos: `GoalkeeperPerformanceEvaluation`
(W25, o veredito final), `GoalkeeperDecisionEvaluationResult.rules_failed`
(W23, para identificar QUAL desvio específico de compatibilidade
motivou a orientação - lido diretamente, nunca recalculado), o
`GoalkeeperDecision` observado (W22) e o `PlayOutcome` observado (W24).

Segue o padrão de composição estabelecido nas W14-W25: instancia
`GoalkeeperPerformanceEvaluationAnalyzer`/`GoalkeeperDecisionEvaluationAnalyzer`/
`PlayOutcomeAnalyzer`/`GoalkeeperDecisionAnalyzer` internamente e chama
`.analyze(football_world)` como função pura em cada um - nenhum canal
de comunicação especial entre Analyzers, nenhuma mudança em
`AnalyzerProcessor`/`ProcessorContext`. Sem `AnalyzerContext` próprio -
quarto combinador puro (depois de `PlaySituationAnalyzer`/W21,
`GoalkeeperDecisionEvaluationAnalyzer`/W23 e
`GoalkeeperPerformanceEvaluationAnalyzer`/W25)."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.base import Analyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperCoachingResult
from worker.analyzers.rules import Rule, RuleOutcome, evaluate_rules
from worker.analyzers.types import (
    AnalyzerName,
    AnalyzerVersion,
    GoalkeeperCoaching,
    GoalkeeperDecision,
    GoalkeeperDecisionEvaluation,
    GoalkeeperPerformanceEvaluation,
    PlayOutcome,
)
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld

_ACTIVE_SHOT_RESPONSES = (
    GoalkeeperDecision.PREPARE_DIVE, GoalkeeperDecision.DIVE_LEFT, GoalkeeperDecision.DIVE_RIGHT,
)
_REINFORCEMENT_PERFORMANCES = (GoalkeeperPerformanceEvaluation.EXCELLENT, GoalkeeperPerformanceEvaluation.GOOD)


@dataclass(frozen=True)
class _CoachingContext:
    """Entrada PURA das regras desta sprint - só campos já ecoados pelos
    Analyzers compostos, nunca recalculados.
    `decision_evaluation_rules_passed`/`decision_evaluation_rules_failed`
    vêm diretamente da Explainability da W23
    (`GoalkeeperDecisionEvaluationResult`) - permitem identificar QUAL
    regra de compatibilidade especificamente falhou, sem reimplementar
    nenhuma lógica de `GoalkeeperDecisionEvaluationAnalyzer`.
    `rules_evaluated` (W23) sempre lista os 6 ids das regras
    independentemente de aplicabilidade (`evaluate_rules()` produz um
    `RuleOutcome` por `Rule`, mesmo quando `passed is None` - ver
    `worker.analyzers.rules`); a APLICABILIDADE de uma regra da W23 só é
    determinável verificando se o id está em `rules_passed` OU
    `rules_failed` (nunca em `rules_evaluated` isoladamente)."""

    performance: GoalkeeperPerformanceEvaluation
    decision_evaluation: GoalkeeperDecisionEvaluation
    decision: GoalkeeperDecision
    outcome: PlayOutcome
    decision_evaluation_rules_passed: tuple[str, ...]
    decision_evaluation_rules_failed: tuple[str, ...]


def _decision_evaluation_rule_was_applicable(ctx: _CoachingContext, rule_id: str) -> bool:
    return rule_id in ctx.decision_evaluation_rules_passed or rule_id in ctx.decision_evaluation_rules_failed


def _evaluation_available(ctx: _CoachingContext) -> bool:
    """Sempre aplicável - espelha o primeiro gate de
    `GoalkeeperPerformanceEvaluationAnalyzer` (W25): sem uma avaliação de
    desempenho estabelecida, nenhuma orientação técnica é possível."""
    return ctx.performance != GoalkeeperPerformanceEvaluation.INSUFFICIENT_INFORMATION


def _decisive_performance_established(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando a regra anterior passou - espelha o segundo
    gate da W25: a avaliação de desempenho precisa ser um veredito
    decisivo (não `UNKNOWN`), não apenas "ainda observando"."""
    if not _evaluation_available(ctx):
        return None
    return ctx.performance != GoalkeeperPerformanceEvaluation.UNKNOWN


def _is_actionable(ctx: _CoachingContext) -> bool:
    return _evaluation_available(ctx) and _decisive_performance_established(ctx) is True


def _performance_was_reinforcement(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando há uma orientação a extrair - identifica os
    dois casos de REFORÇO (desempenho `EXCELLENT`/`GOOD`), em que a
    orientação é "continue fazendo o que já está fazendo", não uma
    correção."""
    if not _is_actionable(ctx):
        return None
    return ctx.performance in _REINFORCEMENT_PERFORMANCES


def _conceded_goal_without_active_response(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando o desempenho não foi de reforço - um gol
    sofrido sem que o goleiro tenha reagido ativamente (nem preparado,
    nem mergulhado) sugere que faltou engajamento com a jogada -
    orientação `ATTACK_BALL` (vir na bola/reduzir o ângulo), não apenas
    reposicionamento passivo."""
    if not _is_actionable(ctx) or ctx.performance in _REINFORCEMENT_PERFORMANCES:
        return None
    if ctx.outcome != PlayOutcome.GOAL:
        return None
    return ctx.decision not in _ACTIVE_SHOT_RESPONSES


def _committed_without_shot(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando a regra `no_dive_without_shot` da W23 foi de
    fato avaliada (a decisão observada foi um mergulho) - lida
    DIRETAMENTE de `rules_failed`, nunca recalculada: um mergulho sem
    chute detectado é um compromisso prematuro - orientação
    `MOVE_LATER` (esperar mais antes de se comprometer)."""
    if not _is_actionable(ctx) or ctx.performance in _REINFORCEMENT_PERFORMANCES:
        return None
    if not _decision_evaluation_rule_was_applicable(ctx, "no_dive_without_shot"):
        return None
    return "no_dive_without_shot" in ctx.decision_evaluation_rules_failed


def _reacted_passively_to_shot(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando a regra `shot_prompts_active_response` da W23
    foi de fato avaliada (um chute foi detectado) - lida DIRETAMENTE de
    `rules_failed`: um chute detectado sem uma reação ativa (preparar/
    mergulhar) sugere que a reação veio tarde demais - orientação
    `MOVE_EARLIER`."""
    if not _is_actionable(ctx) or ctx.performance in _REINFORCEMENT_PERFORMANCES:
        return None
    if not _decision_evaluation_rule_was_applicable(ctx, "shot_prompts_active_response"):
        return None
    return "shot_prompts_active_response" in ctx.decision_evaluation_rules_failed


def _dived_wrong_direction(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando a regra `dive_direction_matches_ball_direction`
    da W23 foi de fato avaliada (o goleiro mergulhou e ambos os sinais
    laterais eram fortes o suficiente) - lida DIRETAMENTE de
    `rules_failed`: mergulhar na direção errada sugere que a leitura da
    jogada foi precipitada - orientação `STAY_PATIENT` (esperar a bola
    se definir antes de se comprometer lateralmente)."""
    if not _is_actionable(ctx) or ctx.performance in _REINFORCEMENT_PERFORMANCES:
        return None
    if not _decision_evaluation_rule_was_applicable(ctx, "dive_direction_matches_ball_direction"):
        return None
    return "dive_direction_matches_ball_direction" in ctx.decision_evaluation_rules_failed


def _recovery_was_insufficient(ctx: _CoachingContext) -> bool | None:
    """Só aplicável quando a decisão observada foi `RECOVER_POSITION` -
    por construção da W22, essa decisão só ocorre depois de um mergulho/
    preparação; se o desempenho ainda assim não foi de reforço, a
    recuperação de posição foi lenta demais para o desfecho da jogada -
    orientação `RECOVER_FASTER`."""
    if not _is_actionable(ctx) or ctx.performance in _REINFORCEMENT_PERFORMANCES:
        return None
    if ctx.decision != GoalkeeperDecision.RECOVER_POSITION:
        return None
    return True


_RULES: list[Rule[_CoachingContext]] = [
    Rule(
        "evaluation_available", "A avaliacao de desempenho (W25) deve estar disponivel (nao INSUFFICIENT_INFORMATION)",
        _evaluation_available,
    ),
    Rule(
        "decisive_performance_established", "A avaliacao de desempenho deve ser decisiva (nao UNKNOWN)",
        _decisive_performance_established,
    ),
    Rule(
        "performance_was_reinforcement", "O desempenho observado foi EXCELLENT ou GOOD (orientacao de reforco)",
        _performance_was_reinforcement,
    ),
    Rule(
        "conceded_goal_without_active_response",
        "Gol sofrido sem nenhuma reacao ativa (preparar/mergulhar) do goleiro",
        _conceded_goal_without_active_response,
    ),
    Rule(
        "committed_without_shot", "Mergulho executado sem nenhum chute detectado (compromisso prematuro)",
        _committed_without_shot,
    ),
    Rule(
        "reacted_passively_to_shot", "Chute detectado sem uma reacao ativa correspondente do goleiro",
        _reacted_passively_to_shot,
    ),
    Rule(
        "dived_wrong_direction", "Mergulho executado na direcao lateral oposta a da bola",
        _dived_wrong_direction,
    ),
    Rule(
        "recovery_was_insufficient", "Reposicionamento apos mergulho/preparacao nao foi suficiente para o desfecho",
        _recovery_was_insufficient,
    ),
]


class GoalkeeperCoachingAnalyzer(Analyzer):
    """Responde apenas: "qual orientação técnica pode ser extraída desta
    jogada?" - classificação determinística e fortemente tipada
    (`GoalkeeperCoaching`), nunca linguagem natural, nunca um relatório
    final."""

    name = "goalkeeper_coaching"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._performance_analyzer = GoalkeeperPerformanceEvaluationAnalyzer(settings)
        self._decision_evaluation_analyzer = GoalkeeperDecisionEvaluationAnalyzer(settings)
        self._play_outcome_analyzer = PlayOutcomeAnalyzer(settings)
        self._goalkeeper_decision_analyzer = GoalkeeperDecisionAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        performance_result = self._performance_analyzer.analyze(football_world)
        decision_evaluation_result = self._decision_evaluation_analyzer.analyze(football_world)
        outcome_result = self._play_outcome_analyzer.analyze(football_world)
        decision_result = self._goalkeeper_decision_analyzer.analyze(football_world)

        context = _CoachingContext(
            performance=performance_result.performance,
            decision_evaluation=decision_evaluation_result.evaluation,
            decision=decision_result.decision,
            outcome=outcome_result.outcome,
            decision_evaluation_rules_passed=tuple(decision_evaluation_result.rules_passed),
            decision_evaluation_rules_failed=tuple(decision_evaluation_result.rules_failed),
        )
        outcomes = evaluate_rules(_RULES, context)
        coaching = self._classify(outcomes, context.performance)

        rules_evaluated = [outcome.rule_id for outcome in outcomes]
        rules_passed = [outcome.rule_id for outcome in outcomes if outcome.passed is True]
        rules_failed = [outcome.rule_id for outcome in outcomes if outcome.passed is False]
        summary = self._build_summary(
            coaching, performance_result.performance, decision_result.decision, outcome_result.outcome, rules_passed,
        )

        confidence = None
        signals = [
            performance_result.confidence, decision_evaluation_result.confidence,
            outcome_result.confidence, decision_result.confidence,
        ]
        if all(signal is not None for signal in signals):
            confidence = min(signals)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperCoachingResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            coaching=coaching,
            performance=performance_result.performance,
            decision_evaluation=decision_evaluation_result.evaluation,
            decision=decision_result.decision,
            outcome=outcome_result.outcome,
            rules_evaluated=rules_evaluated,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            summary=summary,
            confidence=confidence,
        )

    @staticmethod
    def _classify(
        outcomes: list[RuleOutcome], performance: GoalkeeperPerformanceEvaluation,
    ) -> GoalkeeperCoaching:
        """Agrega os `RuleOutcome`s num veredito único - nunca lê nada
        além dos próprios resultados das regras e do `performance` já
        computado (passado explicitamente para os dois casos de
        reforço, que mapeiam 1:1 para um valor de `GoalkeeperPerformanceEvaluation`
        específico, não apenas um booleano agregado).

        `evaluation_available=False` -> `INSUFFICIENT_INFORMATION`.
        `decisive_performance_established=False` (mas o gate anterior
        passou) -> `UNKNOWN`. `performance_was_reinforcement=True` ->
        `NO_FEEDBACK` (desempenho `EXCELLENT`) ou `KEEP_POSITION`
        (desempenho `GOOD`). Caso contrário, percorre as regras
        ESPECÍFICAS em ordem de PRIORIDADE fixa e documentada - a
        primeira que for satisfeita (`True`) determina a orientação;
        nenhuma satisfeita -> `IMPROVE_POSITIONING` (orientação
        residual/genérica, sem nenhum desvio específico auditável
        identificado).

        Ordem de prioridade (mais severa primeiro): gol sofrido sem
        reação ativa (`ATTACK_BALL`) > mergulho sem chute
        (`MOVE_LATER`) > reação passiva a um chute (`MOVE_EARLIER`) >
        mergulho na direção errada (`STAY_PATIENT`) > recuperação
        insuficiente (`RECOVER_FASTER`). Documentada, não uma
        ambiguidade real - mais de uma regra específica pode ser
        aplicável ao mesmo tempo (ex.: reação passiva a um chute que
        termina em gol), e a mais severa/concreta (o gol sofrido)
        prevalece."""
        by_id = {outcome.rule_id: outcome.passed for outcome in outcomes}

        if by_id.get("evaluation_available") is False:
            return GoalkeeperCoaching.INSUFFICIENT_INFORMATION
        if by_id.get("decisive_performance_established") is False:
            return GoalkeeperCoaching.UNKNOWN
        if by_id.get("performance_was_reinforcement"):
            return (
                GoalkeeperCoaching.NO_FEEDBACK if performance == GoalkeeperPerformanceEvaluation.EXCELLENT
                else GoalkeeperCoaching.KEEP_POSITION
            )

        if by_id.get("conceded_goal_without_active_response"):
            return GoalkeeperCoaching.ATTACK_BALL
        if by_id.get("committed_without_shot"):
            return GoalkeeperCoaching.MOVE_LATER
        if by_id.get("reacted_passively_to_shot"):
            return GoalkeeperCoaching.MOVE_EARLIER
        if by_id.get("dived_wrong_direction"):
            return GoalkeeperCoaching.STAY_PATIENT
        if by_id.get("recovery_was_insufficient"):
            return GoalkeeperCoaching.RECOVER_FASTER

        return GoalkeeperCoaching.IMPROVE_POSITIONING

    @staticmethod
    def _build_summary(
        coaching: GoalkeeperCoaching, performance: GoalkeeperPerformanceEvaluation,
        decision: GoalkeeperDecision, outcome: PlayOutcome, rules_passed: list[str],
    ) -> str:
        """String ESTRUTURADA, não linguagem natural (mesmo princípio da
        W25) - suficiente para auditoria sem gerar prosa/coaching em
        texto livre."""
        contributing = ",".join(rules_passed) if rules_passed else "none"
        return (
            f"coaching={coaching.value}; performance={performance.value}; decision={decision.value}; "
            f"outcome={outcome.value}; contributing_rules={contributing}"
        )

    def reset(self) -> None:
        """Delega `reset()` aos quatro Analyzers compostos - dois deles
        (`GoalkeeperDecisionAnalyzer`/`PlayOutcomeAnalyzer`) são
        genuinamente STATEFUL (por transitividade, dentro de
        `GoalkeeperPerformanceEvaluationAnalyzer`/`GoalkeeperDecisionEvaluationAnalyzer`
        também); este Analyzer não tem `AnalyzerContext` próprio -
        combinador puro, mesmo padrão de `PlaySituationAnalyzer` (W21),
        `GoalkeeperDecisionEvaluationAnalyzer` (W23) e
        `GoalkeeperPerformanceEvaluationAnalyzer` (W25)."""
        self._performance_analyzer.reset()
        self._decision_evaluation_analyzer.reset()
        self._play_outcome_analyzer.reset()
        self._goalkeeper_decision_analyzer.reset()
