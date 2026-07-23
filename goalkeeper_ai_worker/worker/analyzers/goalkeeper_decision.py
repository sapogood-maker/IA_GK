"""GoalkeeperDecisionAnalyzer: primeiro Analyzer específico do goleiro
(Sprint W22) - identifica APENAS qual decisão o goleiro APARENTA estar
executando (`GoalkeeperDecision`), a partir do comportamento OBSERVADO.
NUNCA avalia se a decisão foi correta, NUNCA dá nota, NUNCA julga
desempenho, NUNCA avalia o resultado da jogada - é uma CLASSIFICAÇÃO de
comportamento, não uma opinião sobre sua qualidade.

Segue o padrão de composição estabelecido nas W14-W21: instancia
`PlaySituationAnalyzer`/`GoalkeeperPositionAnalyzer`/
`GoalkeeperBallAlignmentAnalyzer`/`BallTrajectoryAnalyzer`/`ShotAnalyzer`
internamente e chama `.analyze(football_world)` como função pura em cada
um - nenhum canal de comunicação especial entre Analyzers, nenhuma
mudança em `AnalyzerProcessor`/`ProcessorContext`. Nenhuma geometria já
calculada por esses cinco Analyzers é recalculada.

`movement_direction`/`movement_speed` são a única informação
GENUINAMENTE NOVA desta sprint: nenhum Analyzer composto rastreia o
movimento do PRÓPRIO goleiro entre frames (`GoalkeeperPositionAnalyzer`
é puramente geométrico, uma fotografia por frame). Por isso este
Analyzer é STATEFUL (quarto `AnalyzerContext` real, depois de
`BallMotionContext`/W18, `ShotAnalyzerContext`/W19,
`BallTrajectoryContext`/W20) - mesma disciplina de continuidade de
`BallMotionAnalyzer`: compara a posição do goleiro atual com a posição
memorizada do frame anterior, usando o mesmo `track_id` (via
`football_world.goalkeepers[0]`, lido diretamente - `GoalkeeperPositionResult`
não expõe `track_id`, mesmo padrão já usado por `BallMotionAnalyzer` para
a bola); qualquer lacuna ou mudança de identidade reinicia a observação,
nunca extrapola."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.context import AnalyzerContext
from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperDecisionResult
from worker.analyzers.shot import ShotAnalyzer
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, GoalkeeperDecision, PlaySituation
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.vector import Vector
from worker.domain.types import EntityId


@dataclass
class GoalkeeperDecisionContext(AnalyzerContext):
    """Memória interna do `GoalkeeperDecisionAnalyzer` entre chamadas
    sucessivas de `analyze()` - a posição/identidade/deslocamento em
    profundidade do goleiro no frame ANTERIOR, mais a última decisão
    classificada (usada para reconhecer `RECOVER_POSITION` logo após um
    mergulho). Pertence ao Job - nunca sobrevive entre Jobs (`reset()`)."""

    previous_position: Coordinate | None = None
    previous_track_id: EntityId | None = None
    previous_depth_offset: float | None = None
    previous_decision: GoalkeeperDecision | None = None

    def reset(self) -> None:
        self.previous_position = None
        self.previous_track_id = None
        self.previous_depth_offset = None
        self.previous_decision = None


class GoalkeeperDecisionAnalyzer(Analyzer):
    """Responde apenas: "qual decisão o goleiro aparenta estar
    executando?" - classificação determinística e fortemente tipada
    (`GoalkeeperDecision`) do comportamento OBSERVADO, nunca uma
    avaliação de mérito."""

    name = "goalkeeper_decision"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._play_situation_analyzer = PlaySituationAnalyzer(settings)
        self._goalkeeper_position_analyzer = GoalkeeperPositionAnalyzer(settings)
        self._goalkeeper_ball_alignment_analyzer = GoalkeeperBallAlignmentAnalyzer(settings)
        self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
        self._shot_analyzer = ShotAnalyzer(settings)
        self._shift_min_speed = settings.goalkeeper_shift_min_speed
        self._dive_min_speed = settings.goalkeeper_dive_min_speed
        self._context = GoalkeeperDecisionContext()

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        play_situation = self._play_situation_analyzer.analyze(football_world)
        goalkeeper_position = self._goalkeeper_position_analyzer.analyze(football_world)
        alignment = self._goalkeeper_ball_alignment_analyzer.analyze(football_world)
        trajectory = self._ball_trajectory_analyzer.analyze(football_world)
        shot = self._shot_analyzer.analyze(football_world)

        ball_detected = play_situation.ball_detected
        goalkeeper_detected = play_situation.goalkeeper_detected
        confidence = self._combined_confidence(goalkeeper_position, alignment, trajectory, shot)

        if not goalkeeper_detected:
            # Sem goleiro visivel - nao ha comportamento nenhum para
            # classificar. Continuidade quebrada: um reaparecimento
            # futuro sera tratado como uma primeira observacao nova.
            self._context.reset()
            return self._result(
                football_world.frame_index, start, decision=GoalkeeperDecision.UNKNOWN,
                play_situation=play_situation.situation, ball_detected=ball_detected,
                goalkeeper_detected=False,
            )

        current_goalkeeper = football_world.goalkeepers[0]
        current_position = goalkeeper_position.goalkeeper_position
        current_track_id = current_goalkeeper.track_id
        current_depth_offset = goalkeeper_position.depth_offset

        is_same_goalkeeper = (
            self._context.previous_position is not None
            and self._context.previous_track_id == current_track_id
        )

        if not is_same_goalkeeper:
            # Primeira observacao deste goleiro (ou o track_id mudou
            # desde o ultimo frame) - nao ha posicao anterior valida
            # para comparar, entao nenhum movimento pode ser inferido.
            result = self._result(
                football_world.frame_index, start, decision=GoalkeeperDecision.UNKNOWN,
                play_situation=play_situation.situation, ball_detected=ball_detected,
                goalkeeper_detected=True, goalkeeper_position=current_position,
                ball_direction=shot.direction_angle, alignment=alignment.is_between_ball_and_goal,
                confidence=confidence,
            )
            self._context.previous_position = current_position
            self._context.previous_track_id = current_track_id
            self._context.previous_depth_offset = current_depth_offset
            self._context.previous_decision = GoalkeeperDecision.UNKNOWN
            return result

        previous_position = self._context.previous_position
        movement_direction = Vector.between(previous_position, current_position)
        movement_speed = movement_direction.magnitude()

        depth_change = None
        if current_depth_offset is not None and self._context.previous_depth_offset is not None:
            depth_change = abs(current_depth_offset) - abs(self._context.previous_depth_offset)

        decision = self._classify(
            shot.shot_detected, movement_speed, movement_direction, depth_change,
            self._context.previous_decision,
        )

        result = self._result(
            football_world.frame_index, start, decision=decision,
            play_situation=play_situation.situation, ball_detected=ball_detected,
            goalkeeper_detected=True, goalkeeper_position=current_position,
            movement_direction=movement_direction, movement_speed=movement_speed,
            ball_direction=shot.direction_angle, alignment=alignment.is_between_ball_and_goal,
            confidence=confidence,
        )

        self._context.previous_position = current_position
        self._context.previous_track_id = current_track_id
        self._context.previous_depth_offset = current_depth_offset
        self._context.previous_decision = decision
        return result

    def _classify(
        self, shot_detected: bool, movement_speed: float, movement_direction: Vector,
        depth_change: float | None, previous_decision: GoalkeeperDecision | None,
    ) -> GoalkeeperDecision:
        """Árvore de decisão determinística, por ordem de PRIORIDADE fixa
        - cada regra olha só para sinais já computados (ou o deslocamento
        do próprio goleiro, calculado acima), nunca recalcula geometria
        de outros Analyzers.

        Eixos: `movement_direction.dy` é o eixo LATERAL (mesma convenção
        de `lateral_offset`/`covers_left_post` - y menor = esquerda);
        `movement_direction.dx` é o eixo de PROFUNDIDADE (mesma convenção
        de `depth_offset`). `depth_change` (fornecido pelo chamador) é a
        variação de `|depth_offset|` entre frames - positivo quando o
        goleiro se afasta da linha do gol (STEP_FORWARD), negativo quando
        se aproxima (STEP_BACK); usar a variação da MAGNITUDE (não o
        sinal cru de `dx`) torna a regra agnóstica a qual dos dois gols
        (`Goal.default_pair()`, W12) o goleiro está defendendo.

        Em caso de EMPATE entre o eixo lateral e o de profundidade
        (`abs(dy) == abs(dx)`), a regra favorece a classificação LATERAL
        (`SHIFT_*`) - desempate determinístico e documentado, não uma
        ambiguidade real."""
        lateral = movement_direction.dy
        depth = movement_direction.dx
        lateral_dominant = abs(lateral) >= abs(depth)

        if shot_detected:
            # Chute detectado - o goleiro esta reagindo (ou deveria
            # estar). PREPARE_DIVE e um PROXY deterministico baseado em
            # velocidade observada (nao ha estimativa de pose/postura
            # real neste Worker) - documentado como limitacao honesta em
            # GoalkeeperDecision.
            if movement_speed >= self._dive_min_speed and lateral_dominant and lateral != 0.0:
                return GoalkeeperDecision.DIVE_LEFT if lateral < 0 else GoalkeeperDecision.DIVE_RIGHT
            return GoalkeeperDecision.PREPARE_DIVE

        was_diving = previous_decision in (
            GoalkeeperDecision.DIVE_LEFT, GoalkeeperDecision.DIVE_RIGHT, GoalkeeperDecision.PREPARE_DIVE,
        )
        if was_diving and movement_speed >= self._shift_min_speed:
            return GoalkeeperDecision.RECOVER_POSITION

        if movement_speed < self._shift_min_speed:
            return GoalkeeperDecision.STAY_ON_LINE

        if lateral_dominant:
            return GoalkeeperDecision.SHIFT_LEFT if lateral < 0 else GoalkeeperDecision.SHIFT_RIGHT

        if depth_change is None:
            return GoalkeeperDecision.UNKNOWN
        return GoalkeeperDecision.STEP_FORWARD if depth_change > 0 else GoalkeeperDecision.STEP_BACK

    @staticmethod
    def _combined_confidence(goalkeeper_position, alignment, trajectory, shot) -> float | None:
        """Usa apenas sinais reais já disponíveis - nunca inventa uma
        probabilidade. `None` a menos que os quatro Analyzers compostos
        tenham produzido um `confidence` real."""
        signals = [
            goalkeeper_position.confidence, alignment.confidence, trajectory.confidence, shot.confidence,
        ]
        if all(signal is not None for signal in signals):
            return min(signals)
        return None

    def _result(
        self, frame_index: int, start: float, *, decision: GoalkeeperDecision,
        play_situation: PlaySituation, ball_detected: bool, goalkeeper_detected: bool,
        goalkeeper_position: Coordinate | None = None, movement_direction: Vector | None = None,
        movement_speed: float | None = None, ball_direction: float | None = None,
        alignment: bool | None = None, confidence: float | None = None,
    ) -> GoalkeeperDecisionResult:
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperDecisionResult(
            frame_index=frame_index,
            metadata=metadata,
            decision=decision,
            play_situation=play_situation,
            ball_detected=ball_detected,
            goalkeeper_detected=goalkeeper_detected,
            goalkeeper_position=goalkeeper_position,
            movement_direction=movement_direction,
            movement_speed=movement_speed,
            ball_direction=ball_direction,
            alignment=alignment,
            confidence=confidence,
        )

    def reset(self) -> None:
        """Limpa a memória de posição/decisão do goleiro e delega
        `reset()` aos cinco Analyzers compostos - mesma disciplina já
        aplicada por `ShotAnalyzer.reset()` (W19)/`BallTrajectoryAnalyzer.
        reset()` (W20)/`PlaySituationAnalyzer.reset()` (W21)."""
        self._context.reset()
        self._play_situation_analyzer.reset()
        self._goalkeeper_position_analyzer.reset()
        self._goalkeeper_ball_alignment_analyzer.reset()
        self._ball_trajectory_analyzer.reset()
        self._shot_analyzer.reset()
