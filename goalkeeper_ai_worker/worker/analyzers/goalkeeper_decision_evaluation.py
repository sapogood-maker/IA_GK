"""GoalkeeperDecisionEvaluationAnalyzer: primeiro Analyzer de AVALIAÇÃO
(Sprint W23) - responde APENAS "a decisão observada do goleiro foi
COMPATÍVEL com a situação observada?". NUNCA avalia o resultado da
jogada (não determina se houve defesa ou gol), NUNCA julga desempenho -
verifica CONSISTÊNCIA lógica entre `PlaySituation` (W21) e
`GoalkeeperDecision` (W22), via um mecanismo explícito e auditável de
Rule Evaluation (`worker.analyzers.rules`, novo módulo genérico desta
sprint).

Separação rigorosa de camadas (Observação → Situação → Decisão →
Avaliação): esta sprint NUNCA modifica ou reinterpreta os resultados dos
Analyzers anteriores - só os COMBINA como entrada das regras.

Segue o padrão de composição estabelecido nas W14-W22: instancia
`PlaySituationAnalyzer`/`GoalkeeperDecisionAnalyzer`/
`GoalkeeperPositionAnalyzer`/`GoalkeeperBallAlignmentAnalyzer`/
`BallTrajectoryAnalyzer`/`ShotAnalyzer` internamente e chama
`.analyze(football_world)` como função pura em cada um - nenhum canal de
comunicação especial entre Analyzers, nenhuma mudança em
`AnalyzerProcessor`/`ProcessorContext`. `GoalkeeperPositionAnalyzer`/
`GoalkeeperBallAlignmentAnalyzer`/`BallTrajectoryAnalyzer` não
contribuem para nenhuma regra de conteúdo diretamente - só fornecem
sinais adicionais reais de `confidence` (mesmo princípio já usado por
`BallTrajectoryAnalyzer` compondo `GoalGeometryAnalyzer` na W20).

Explainability: o resultado nunca é um estado isolado - sempre vem
acompanhado de `rules_evaluated`/`rules_passed`/`rules_failed`/
`explanations`, permitindo auditar exatamente quais regras levaram a
cada veredito."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperDecisionEvaluationResult
from worker.analyzers.rules import Rule, evaluate_rules
from worker.analyzers.shot import ShotAnalyzer
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, GoalkeeperDecision, GoalkeeperDecisionEvaluation, PlaySituation
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld

_DIVE_DECISIONS = (GoalkeeperDecision.DIVE_LEFT, GoalkeeperDecision.DIVE_RIGHT)
_ACTIVE_SHOT_RESPONSES = (
    GoalkeeperDecision.PREPARE_DIVE, GoalkeeperDecision.DIVE_LEFT, GoalkeeperDecision.DIVE_RIGHT,
)


@dataclass(frozen=True)
class _EvaluationContext:
    """Entrada PURA das regras desta sprint - só os campos já ecoados
    pelos Analyzers compostos, nunca recalculados."""

    ball_detected: bool
    goalkeeper_detected: bool
    situation: PlaySituation
    decision: GoalkeeperDecision
    goalkeeper_lateral: float | None
    ball_lateral: float | None
    min_lateral_signal: float


def _actors_visible(ctx: _EvaluationContext) -> bool:
    """Sempre aplicável - a bola e o goleiro precisam estar visíveis
    para que qualquer avaliação de compatibilidade faça sentido."""
    return ctx.ball_detected and ctx.goalkeeper_detected


def _decision_established(ctx: _EvaluationContext) -> bool | None:
    """Só aplicável quando os atores estão visíveis - senão a decisão já
    é trivialmente UNKNOWN pela própria ausência (capturado pela regra
    `actors_visible`, não duplicado aqui)."""
    if not (ctx.ball_detected and ctx.goalkeeper_detected):
        return None
    return ctx.decision != GoalkeeperDecision.UNKNOWN


def _shot_prompts_active_response(ctx: _EvaluationContext) -> bool | None:
    """Só aplicável quando um chute foi detectado - nesse caso, a
    decisão esperada é uma reação ativa (preparar/mergulhar), não ficar
    parado ou se reposicionar lateralmente/em profundidade sem relação
    com o chute."""
    if ctx.situation != PlaySituation.SHOT_DETECTED:
        return None
    return ctx.decision in _ACTIVE_SHOT_RESPONSES


def _no_dive_without_shot(ctx: _EvaluationContext) -> bool | None:
    """Só aplicável quando a decisão foi um mergulho - checagem cruzada
    de consistência entre `GoalkeeperDecisionAnalyzer` (W22) e
    `ShotAnalyzer`/`PlaySituationAnalyzer` (W19/W21): um mergulho sem
    chute detectado seria logicamente incompatível (por construção do
    W22, isso não deveria acontecer - esta regra existe para auditar
    essa garantia de forma independente, não para redescobri-la)."""
    if ctx.decision not in _DIVE_DECISIONS:
        return None
    return ctx.situation == PlaySituation.SHOT_DETECTED


def _recover_follows_shot_ending(ctx: _EvaluationContext) -> bool | None:
    """Só aplicável quando a decisão foi RECOVER_POSITION - por
    definição (W22), essa decisão só ocorre depois que o chute deixou de
    ser detectado; esta regra audita essa garantia de forma
    independente."""
    if ctx.decision != GoalkeeperDecision.RECOVER_POSITION:
        return None
    return ctx.situation != PlaySituation.SHOT_DETECTED


def _dive_direction_matches_ball_direction(ctx: _EvaluationContext) -> bool | None:
    """Só aplicável quando a decisão foi um mergulho E ambos os sinais
    de direção lateral (goleiro e bola) são fortes o suficiente
    (`>= min_lateral_signal`) para não julgar ruído de detecção como uma
    direção real."""
    if ctx.decision not in _DIVE_DECISIONS:
        return None
    if ctx.goalkeeper_lateral is None or ctx.ball_lateral is None:
        return None
    if abs(ctx.goalkeeper_lateral) < ctx.min_lateral_signal or abs(ctx.ball_lateral) < ctx.min_lateral_signal:
        return None
    return (ctx.goalkeeper_lateral < 0) == (ctx.ball_lateral < 0)


_RULES: list[Rule[_EvaluationContext]] = [
    Rule("actors_visible", "Bola e goleiro devem estar visiveis para permitir avaliacao", _actors_visible),
    Rule(
        "decision_established", "A decisao do goleiro deve estar estabelecida (nao UNKNOWN)",
        _decision_established,
    ),
    Rule(
        "shot_prompts_active_response",
        "Um chute detectado espera uma reacao ativa (preparar/mergulhar)",
        _shot_prompts_active_response,
    ),
    Rule(
        "no_dive_without_shot", "Um mergulho so e compativel se um chute foi detectado",
        _no_dive_without_shot,
    ),
    Rule(
        "recover_follows_shot_ending",
        "RECOVER_POSITION so e compativel apos o chute deixar de ser detectado",
        _recover_follows_shot_ending,
    ),
    Rule(
        "dive_direction_matches_ball_direction",
        "A direcao do mergulho deve coincidir com a direcao lateral observada da bola",
        _dive_direction_matches_ball_direction,
    ),
]


class GoalkeeperDecisionEvaluationAnalyzer(Analyzer):
    """Responde apenas: "a decisão observada do goleiro foi compatível
    com a situação observada?" - nunca avalia se houve defesa, gol, ou
    se a decisão foi de boa qualidade."""

    name = "goalkeeper_decision_evaluation"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._play_situation_analyzer = PlaySituationAnalyzer(settings)
        self._goalkeeper_decision_analyzer = GoalkeeperDecisionAnalyzer(settings)
        self._goalkeeper_position_analyzer = GoalkeeperPositionAnalyzer(settings)
        self._goalkeeper_ball_alignment_analyzer = GoalkeeperBallAlignmentAnalyzer(settings)
        self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
        self._shot_analyzer = ShotAnalyzer(settings)
        self._min_lateral_signal = settings.goalkeeper_evaluation_min_lateral_signal

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        play_situation = self._play_situation_analyzer.analyze(football_world)
        decision_result = self._goalkeeper_decision_analyzer.analyze(football_world)
        goalkeeper_position = self._goalkeeper_position_analyzer.analyze(football_world)
        alignment = self._goalkeeper_ball_alignment_analyzer.analyze(football_world)
        trajectory = self._ball_trajectory_analyzer.analyze(football_world)
        shot = self._shot_analyzer.analyze(football_world)

        goalkeeper_lateral = (
            decision_result.movement_direction.dy if decision_result.movement_direction is not None else None
        )
        # shot.direction_vector e NORMALIZADO (Vector.normalized(), ver
        # BallMotionAnalyzer/W18) - multiplicar pela velocidade escalar
        # (shot.ball_speed) reconstrói a componente lateral RAW (mesma
        # escala de pixels/frame de `goalkeeper_lateral`), sem recalcular
        # nenhuma geometria - só recombina dois campos já produzidos.
        ball_lateral = (
            shot.direction_vector.dy * shot.ball_speed
            if shot.direction_vector is not None and shot.ball_speed is not None else None
        )

        context = _EvaluationContext(
            ball_detected=play_situation.ball_detected,
            goalkeeper_detected=play_situation.goalkeeper_detected,
            situation=play_situation.situation,
            decision=decision_result.decision,
            goalkeeper_lateral=goalkeeper_lateral,
            ball_lateral=ball_lateral,
            min_lateral_signal=self._min_lateral_signal,
        )

        outcomes = evaluate_rules(_RULES, context)
        evaluation = self._classify(outcomes)

        rules_evaluated = [outcome.rule_id for outcome in outcomes]
        rules_passed = [outcome.rule_id for outcome in outcomes if outcome.passed is True]
        rules_failed = [outcome.rule_id for outcome in outcomes if outcome.passed is False]
        explanations = [outcome.explanation for outcome in outcomes]

        confidence = None
        signals = [
            play_situation.confidence, decision_result.confidence, goalkeeper_position.confidence,
            alignment.confidence, trajectory.confidence, shot.confidence,
        ]
        if all(signal is not None for signal in signals):
            confidence = min(signals)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperDecisionEvaluationResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            evaluation=evaluation,
            play_situation=play_situation.situation,
            goalkeeper_decision=decision_result.decision,
            rules_evaluated=rules_evaluated,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            explanations=explanations,
            confidence=confidence,
        )

    @staticmethod
    def _classify(outcomes: list) -> GoalkeeperDecisionEvaluation:
        """Agrega os `RuleOutcome`s num veredito único - nunca lê nada
        além dos próprios resultados das regras (a árvore de agregação é
        deterministica e documentada, não uma heurística opaca).

        `actors_visible=False` -> INSUFFICIENT_INFORMATION (nem sequer
        dá para observar quem está em cena). `decision_established=False`
        (mas atores visíveis) -> UNKNOWN (histórico insuficiente para o
        GoalkeeperDecisionAnalyzer estabelecer uma decisão, W22) - uma
        causa DIFERENTE de incerteza, não confundida com a anterior.
        Caso contrário, agrega só as regras de CONTEÚDO que foram
        aplicáveis (`passed is not None`): todas satisfeitas ->
        COMPATIBLE; todas violadas -> INCOMPATIBLE; mistura ->
        PARTIALLY_COMPATIBLE; nenhuma regra de conteúdo aplicável (ex.:
        bola parada, goleiro parado - nada a contradizer) -> COMPATIBLE
        por padrão (ausência de incompatibilidade observada)."""
        by_id = {outcome.rule_id: outcome.passed for outcome in outcomes}

        if by_id.get("actors_visible") is False:
            return GoalkeeperDecisionEvaluation.INSUFFICIENT_INFORMATION
        if by_id.get("decision_established") is False:
            return GoalkeeperDecisionEvaluation.UNKNOWN

        content_results = [
            passed for rule_id, passed in by_id.items()
            if rule_id not in ("actors_visible", "decision_established") and passed is not None
        ]
        if not content_results or all(content_results):
            return GoalkeeperDecisionEvaluation.COMPATIBLE
        if not any(content_results):
            return GoalkeeperDecisionEvaluation.INCOMPATIBLE
        return GoalkeeperDecisionEvaluation.PARTIALLY_COMPATIBLE

    def reset(self) -> None:
        """Delega `reset()` aos seis Analyzers compostos - três deles
        (`GoalkeeperDecisionAnalyzer`/`ShotAnalyzer`/`BallTrajectoryAnalyzer`)
        são genuinamente STATEFUL; os demais são no-op, chamados por
        completude (mesmo princípio já aplicado por `ShotAnalyzer.reset()`,
        W19). Este Analyzer não tem `AnalyzerContext` próprio - é um
        combinador puro, mesmo padrão de `PlaySituationAnalyzer` (W21)."""
        self._play_situation_analyzer.reset()
        self._goalkeeper_decision_analyzer.reset()
        self._goalkeeper_position_analyzer.reset()
        self._goalkeeper_ball_alignment_analyzer.reset()
        self._ball_trajectory_analyzer.reset()
        self._shot_analyzer.reset()
