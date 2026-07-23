"""PlayOutcomeAnalyzer: encerra a cadeia de observação do sistema
(Sprint W24) - responde APENAS "qual foi o resultado OBSERVADO da
jogada?" (`PlayOutcome`, fortemente tipado). NUNCA avalia o goleiro,
NUNCA atribui nota, NUNCA julga a qualidade da decisão - é a última
camada puramente OBSERVACIONAL antes de uma futura avaliação completa de
desempenho (W25+, que combinará `PlaySituationResult`/
`GoalkeeperDecisionResult`/`GoalkeeperDecisionEvaluationResult`/
`PlayOutcomeResult`).

Cadeia completa desta arquitetura: Observação (W13-W20, factual/
geométrico/cinemático) → Situação (W21, `PlaySituationAnalyzer`,
classificação do estado observado) → Decisão (W22,
`GoalkeeperDecisionAnalyzer`, classificação do comportamento do goleiro)
→ Avaliação (W23, `GoalkeeperDecisionEvaluationAnalyzer`, compatibilidade
decisão-situação via Rule Evaluation) → Resultado (W24, esta sprint,
resultado observado da jogada). Cada camada só COMBINA a anterior, nunca
a modifica ou reinterpreta.

Segue o padrão de composição estabelecido nas W14-W23: instancia
`PlaySituationAnalyzer`/`ShotAnalyzer`/`BallTrajectoryAnalyzer`/
`GoalGeometryAnalyzer`/`GoalkeeperDecisionAnalyzer` internamente e chama
`.analyze(football_world)` como função pura em cada um - nenhum canal de
comunicação especial entre Analyzers, nenhuma mudança em
`AnalyzerProcessor`/`ProcessorContext`. Por instrução explícita desta
sprint, NÃO reutiliza o mecanismo de Rule Evaluation da W23
(`worker.analyzers.rules`) - `supporting_evidence` é uma lista simples de
frases, suficiente para esta sprint.

Quinto Analyzer STATEFUL (`PlayOutcomeContext`, depois de
`BallMotionContext`/W18, `ShotAnalyzerContext`/W19,
`BallTrajectoryContext`/W20, `GoalkeeperDecisionContext`/W22): precisa
memorizar a ÚLTIMA posição conhecida da bola/do goleiro (para que
`LOST_TRACK` carregue alguma evidência posicional útil) e se a bola
estava sendo rastreada no frame anterior (para distinguir `LOST_TRACK`
de `INSUFFICIENT_INFORMATION` - a bola nunca apareceu vs. a bola sumiu
no meio da observação)."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.context import AnalyzerContext
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, PlayOutcomeResult
from worker.analyzers.shot import ShotAnalyzer
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, GoalZone, PlayOutcome
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.region import Region


@dataclass
class PlayOutcomeContext(AnalyzerContext):
    """Memória interna do `PlayOutcomeAnalyzer` entre chamadas
    sucessivas de `analyze()` - a última posição conhecida da bola/do
    goleiro (sobrevive a um frame em que um deles some momentaneamente)
    e se a bola estava sendo rastreada continuamente no frame anterior
    (para reconhecer `LOST_TRACK`). Pertence ao Job - nunca sobrevive
    entre Jobs (`reset()`)."""

    was_tracking: bool = False
    last_known_ball_position: Coordinate | None = None
    last_known_goalkeeper_position: Coordinate | None = None

    def reset(self) -> None:
        self.was_tracking = False
        self.last_known_ball_position = None
        self.last_known_goalkeeper_position = None


class PlayOutcomeAnalyzer(Analyzer):
    """Responde apenas: "qual foi o resultado observado da jogada?" -
    classificação determinística e fortemente tipada (`PlayOutcome`) de
    fatos geométricos já disponíveis, nunca uma avaliação de mérito."""

    name = "play_outcome"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._play_situation_analyzer = PlaySituationAnalyzer(settings)
        self._shot_analyzer = ShotAnalyzer(settings)
        self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._goalkeeper_decision_analyzer = GoalkeeperDecisionAnalyzer(settings)
        self._post_proximity_px = settings.outcome_post_proximity_px
        self._save_proximity_px = settings.outcome_save_proximity_px
        self._context = PlayOutcomeContext()

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        play_situation = self._play_situation_analyzer.analyze(football_world)
        shot = self._shot_analyzer.analyze(football_world)
        trajectory = self._ball_trajectory_analyzer.analyze(football_world)
        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)
        decision_result = self._goalkeeper_decision_analyzer.analyze(football_world)

        ball_detected = play_situation.ball_detected
        goalkeeper_detected = play_situation.goalkeeper_detected
        ball_visible = trajectory.ball_detected
        goal_visible = goal_geometry.goal_detected
        shot_detected = shot.shot_detected
        was_tracking_before = self._context.was_tracking

        current_ball_position = (
            trajectory.trajectory_points[-1] if trajectory.trajectory_points else None
        )
        if current_ball_position is not None:
            self._context.last_known_ball_position = current_ball_position
        if decision_result.goalkeeper_position is not None:
            self._context.last_known_goalkeeper_position = decision_result.goalkeeper_position

        ball_last_position = self._context.last_known_ball_position
        goalkeeper_last_position = self._context.last_known_goalkeeper_position

        outcome, supporting_evidence = self._classify(
            ball_detected=ball_detected, goal_visible=goal_visible,
            was_tracking_before=was_tracking_before, trajectory_detected=trajectory.trajectory_detected,
            shot_detected=shot_detected, ball_last_position=ball_last_position,
            goalkeeper_last_position=goalkeeper_last_position,
            goal_regions=goal_geometry.goal_regions, left_post=goal_geometry.left_post,
            right_post=goal_geometry.right_post, direction_changes=trajectory.direction_changes,
            field_region=football_world.field.region,
        )

        self._context.was_tracking = ball_detected and trajectory.trajectory_detected

        confidence = None
        signals = [
            play_situation.confidence, shot.confidence, trajectory.confidence,
            goal_geometry.confidence, decision_result.confidence,
        ]
        if all(signal is not None for signal in signals):
            confidence = min(signals)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return PlayOutcomeResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            outcome=outcome,
            play_situation=play_situation.situation,
            shot_detected=shot_detected,
            ball_detected=ball_detected,
            goalkeeper_detected=goalkeeper_detected,
            ball_visible=ball_visible,
            goal_visible=goal_visible,
            ball_last_position=ball_last_position,
            goalkeeper_last_position=goalkeeper_last_position,
            supporting_evidence=supporting_evidence,
            confidence=confidence,
        )

    def _classify(
        self, *, ball_detected: bool, goal_visible: bool, was_tracking_before: bool,
        trajectory_detected: bool, shot_detected: bool, ball_last_position: Coordinate | None,
        goalkeeper_last_position: Coordinate | None, goal_regions: dict[GoalZone, Region] | None,
        left_post: Coordinate | None, right_post: Coordinate | None, direction_changes: int,
        field_region: Region,
    ) -> tuple[PlayOutcome, list[str]]:
        """Árvore de decisão determinística, por ordem de PRIORIDADE fixa
        - cada regra olha só para fatos já computados (ou lidos
        diretamente de `FootballWorld`, permitido pelo Boundary
        Enforcement), nunca recalcula geometria de outro Analyzer.

        1. Sem geometria do gol, nenhuma classificação geométrica é
           possível -> INSUFFICIENT_INFORMATION.
        2. Bola ausente AGORA mas rastreada no frame anterior ->
           LOST_TRACK (distinto de nunca ter aparecido).
        3. Bola ausente e nunca foi rastreada -> INSUFFICIENT_INFORMATION.
        4. Bola presente mas sem histórico suficiente (primeira
           observação) -> UNKNOWN.
        5. Nenhum chute detectado -> NO_SHOT_DETECTED (a jogada ainda
           não chegou a um chute, não há resultado para reportar).
        6. Chute detectado - classificação geométrica, nesta ordem:
           GOAL (bola dentro de alguma zona do gol) > POST (bola perto
           de um poste) > SAVE (goleiro perto o suficiente da bola) >
           BLOCKED (trajetória mostra uma mudança de direção, indicando
           desvio) > BALL_OUT (bola fora da região do campo) > UNKNOWN
           (nenhuma condição geométrica determinável ainda - bola
           provavelmente ainda em voo)."""
        evidence: list[str] = []

        if not goal_visible:
            evidence.append("geometria do gol nao disponivel neste frame")
            return PlayOutcome.INSUFFICIENT_INFORMATION, evidence

        if not ball_detected:
            if was_tracking_before:
                evidence.append("bola estava sendo rastreada e desapareceu neste frame")
                return PlayOutcome.LOST_TRACK, evidence
            evidence.append("bola nao detectada")
            return PlayOutcome.INSUFFICIENT_INFORMATION, evidence

        if not trajectory_detected:
            evidence.append("primeira observacao da bola - historico insuficiente")
            return PlayOutcome.UNKNOWN, evidence

        if not shot_detected:
            evidence.append("nenhum chute detectado ate agora")
            return PlayOutcome.NO_SHOT_DETECTED, evidence

        evidence.append("chute detectado")

        if ball_last_position is not None and goal_regions:
            for zone, region in goal_regions.items():
                if region.contains(ball_last_position):
                    evidence.append(f"posicao da bola dentro da zona do gol '{zone}'")
                    return PlayOutcome.GOAL, evidence

        if ball_last_position is not None:
            for post_name, post in (("left_post", left_post), ("right_post", right_post)):
                if post is None:
                    continue
                post_distance = float(distance(ball_last_position, post))
                if post_distance <= self._post_proximity_px:
                    evidence.append(f"posicao da bola a {post_distance:.1f}px de {post_name}")
                    return PlayOutcome.POST, evidence

        if ball_last_position is not None and goalkeeper_last_position is not None:
            gk_distance = float(distance(ball_last_position, goalkeeper_last_position))
            if gk_distance <= self._save_proximity_px:
                evidence.append(f"goleiro a {gk_distance:.1f}px da bola")
                return PlayOutcome.SAVE, evidence

        if direction_changes >= 1:
            evidence.append(f"trajetoria registrou {direction_changes} mudanca(s) de direcao")
            return PlayOutcome.BLOCKED, evidence

        if ball_last_position is not None and not field_region.contains(ball_last_position):
            evidence.append("posicao da bola fora da regiao do campo")
            return PlayOutcome.BALL_OUT, evidence

        evidence.append("chute detectado, mas nenhuma condicao geometrica de resultado foi atingida ainda")
        return PlayOutcome.UNKNOWN, evidence

    def reset(self) -> None:
        """Limpa a memória de posição/rastreamento e delega `reset()`
        aos cinco Analyzers compostos - mesma disciplina já aplicada por
        `ShotAnalyzer.reset()` (W19)."""
        self._context.reset()
        self._play_situation_analyzer.reset()
        self._shot_analyzer.reset()
        self._ball_trajectory_analyzer.reset()
        self._goal_geometry_analyzer.reset()
        self._goalkeeper_decision_analyzer.reset()
