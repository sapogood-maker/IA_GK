"""BallTrajectoryAnalyzer: modela a trajetória OBSERVADA da bola ao longo
de múltiplos frames consecutivos (Sprint W20). NUNCA detecta gol, NUNCA
avalia defesa, NUNCA julga decisões do goleiro, NUNCA prevê posições
futuras - toda informação vem exclusivamente dos frames já observados.

Segue o padrão de composição estabelecido nas W14-W19: instancia
`BallMotionAnalyzer`/`BallPositionAnalyzer`/`GoalGeometryAnalyzer`
internamente e chama `.analyze(football_world)` como função pura em cada
um - nenhum canal de comunicação especial entre Analyzers, nenhuma
mudança em `AnalyzerProcessor`/`ProcessorContext`. Nenhuma informação já
disponível nesses três resultados é recalculada; a única informação
genuinamente nova desta sprint é a FORMA da trajetória acumulada
(comprimento do caminho, direção dominante, consistência de direção,
mudanças de direção, linearidade).

`GoalGeometryAnalyzer` é composto (exigido pela sprint) mas nenhum campo
de trajetória depende de posição/geometria do gol - a trajetória é
descrita inteiramente em relação a si mesma. Sua única contribuição é um
terceiro sinal real de confiança (validade estrutural do gol), somado
aos dois já usados por `ShotAnalyzer` (W19) - mesma filosofia de "usar
apenas sinais realmente disponíveis, nunca inventar probabilidades".

Terceiro Analyzer STATEFUL (depois de `BallMotionAnalyzer` W18 e
`ShotAnalyzer` W19): usa `AnalyzerContext` para acumular a sequência de
posições da MESMA bola continuamente observada. `reset()` limpa esse
estado - nenhuma trajetória sobrevive entre Jobs.

Risco 34 (W19, descompasso de escala entre a geometria placeholder do
gol e as posições reais em pixel) permanece inalterado nesta sprint:
como nenhum cálculo de trajetória aqui referencia `goal_center`, todos
os pontos acumulados usam sempre a mesma escala (pixels crus da bola) -
não há novo descompasso introduzido, mas também não há correção do
Risco 34 (fora do escopo desta sprint, por instrução explícita)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from worker.analyzers.ball_motion import BallMotionAnalyzer
from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.context import AnalyzerContext
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, BallTrajectoryResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.vector import Vector, angle_between


@dataclass
class BallTrajectoryContext(AnalyzerContext):
    """Memória interna do `BallTrajectoryAnalyzer` entre chamadas
    sucessivas de `analyze()` - a sequência de posições da MESMA bola
    continuamente observada (sem lacuna de frames, sem mudança de
    `track_id`). Pertence ao Job - nunca sobrevive entre Jobs
    (`reset()`)."""

    points: list[Coordinate] = field(default_factory=list)

    def reset(self) -> None:
        self.points = []


class BallTrajectoryAnalyzer(Analyzer):
    """Responde apenas: "como a bola se moveu, observada até agora?" -
    sequência de posições, comprimento acumulado do caminho percorrido,
    direção dominante, consistência de direção, número de mudanças de
    direção, e o quanto o caminho se aproxima de uma reta. Nunca prevê
    posições futuras, nunca extrapola."""

    name = "ball_trajectory"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._ball_motion_analyzer = BallMotionAnalyzer(settings)
        self._ball_position_analyzer = BallPositionAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._direction_change_threshold_degrees = (
            settings.trajectory_direction_change_threshold_degrees
        )
        self._context = BallTrajectoryContext()

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        ball_motion = self._ball_motion_analyzer.analyze(football_world)
        ball_position = self._ball_position_analyzer.analyze(football_world)
        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)

        if not ball_motion.ball_detected:
            # Bola sumiu deste frame - mesma disciplina de continuidade
            # do BallMotionAnalyzer (W18): nunca inferimos atraves de uma
            # lacuna, entao a trajetoria acumulada e descartada. Um
            # reaparecimento futuro comeca uma trajetoria nova, nunca
            # emenda com a trajetoria anterior.
            self._context.reset()
            return self._result(football_world.frame_index, start, ball_detected=False)

        current_position = ball_motion.current_position
        is_fresh_start = ball_motion.previous_position is None

        if is_fresh_start:
            # Primeira observacao desta bola OU o track_id mudou/houve
            # lacuna desde o ultimo frame (mesmo sinal ja calculado por
            # BallMotionAnalyzer, W18) - comeca uma trajetoria nova.
            self._context.points = [current_position]
        else:
            self._context.points.append(current_position)

        points = list(self._context.points)
        frames_observed = len(points)
        trajectory_detected = frames_observed >= 2

        segments = [
            Vector.between(points[i], points[i + 1]) for i in range(len(points) - 1)
        ]
        trajectory_length = sum(segment.magnitude() for segment in segments)

        average_velocity: Vector | None = None
        dominant_direction: float | None = None
        direction_consistency: float | None = None
        linearity_score: float | None = None

        if segments:
            average_velocity = Vector(
                dx=sum(segment.dx for segment in segments) / len(segments),
                dy=sum(segment.dy for segment in segments) / len(segments),
            )
            if average_velocity.magnitude() > 0.0:
                dominant_direction = float(average_velocity.angle_degrees())

            unit_dx = sum(segment.normalized().dx for segment in segments)
            unit_dy = sum(segment.normalized().dy for segment in segments)
            direction_consistency = Vector(dx=unit_dx, dy=unit_dy).magnitude() / len(segments)

            if trajectory_length > 0.0:
                straight_line_distance = float(distance(points[0], points[-1]))
                linearity_score = straight_line_distance / trajectory_length

        direction_changes = 0
        for i in range(len(segments) - 1):
            deviation = float(angle_between(segments[i], segments[i + 1]))
            if deviation >= self._direction_change_threshold_degrees:
                direction_changes += 1

        confidence = None
        if (
            ball_motion.confidence is not None
            and ball_position.confidence is not None
            and goal_geometry.confidence is not None
        ):
            confidence = min(ball_motion.confidence, ball_position.confidence, goal_geometry.confidence)

        return self._result(
            football_world.frame_index, start, ball_detected=True,
            trajectory_detected=trajectory_detected, trajectory_points=points,
            trajectory_length=trajectory_length, dominant_direction=dominant_direction,
            average_velocity=average_velocity, direction_consistency=direction_consistency,
            direction_changes=direction_changes, linearity_score=linearity_score,
            frames_observed=frames_observed, confidence=confidence,
        )

    def _result(
        self, frame_index: int, start: float, *, ball_detected: bool,
        trajectory_detected: bool = False, trajectory_points: list[Coordinate] | None = None,
        trajectory_length: float | None = None, dominant_direction: float | None = None,
        average_velocity: Vector | None = None, direction_consistency: float | None = None,
        direction_changes: int = 0, linearity_score: float | None = None,
        frames_observed: int = 0, confidence: float | None = None,
    ) -> BallTrajectoryResult:
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return BallTrajectoryResult(
            frame_index=frame_index,
            metadata=metadata,
            ball_detected=ball_detected,
            trajectory_detected=trajectory_detected,
            trajectory_points=trajectory_points,
            trajectory_length=trajectory_length,
            dominant_direction=dominant_direction,
            average_velocity=average_velocity,
            direction_consistency=direction_consistency,
            direction_changes=direction_changes,
            linearity_score=linearity_score,
            frames_observed=frames_observed,
            confidence=confidence,
        )

    def reset(self) -> None:
        """Limpa a trajetória acumulada e delega aos três Analyzers
        compostos - mesma disciplina já aplicada por `ShotAnalyzer.reset()`
        (W19)."""
        self._context.reset()
        self._ball_motion_analyzer.reset()
        self._ball_position_analyzer.reset()
        self._goal_geometry_analyzer.reset()
