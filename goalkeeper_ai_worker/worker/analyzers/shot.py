"""ShotAnalyzer: primeiro Analyzer de EVENTOS (Sprint W19) - identifica
se houve um evento compatível com um chute. NUNCA detecta gol, NUNCA
avalia defesa, NUNCA avalia qualidade, NUNCA prevê trajetória futura -
trabalha exclusivamente com o histórico já observado.

Segue o padrão de composição estabelecido nas W14-W18: instancia
`BallMotionAnalyzer`/`BallPositionAnalyzer`/`GoalGeometryAnalyzer`
internamente e chama `.analyze(football_world)` como função pura em cada
um - nenhum canal de comunicação especial entre Analyzers, nenhuma
mudança em `AnalyzerProcessor`/`ProcessorContext`. Nenhuma informação já
disponível nesses três resultados é recalculada.

Segundo Analyzer STATEFUL (depois de `BallMotionAnalyzer`, W18): precisa
lembrar por quantos frames CONSECUTIVOS os critérios de chute vêm sendo
satisfeitos, para exigir "movimento contínuo" em vez de um pico isolado
de velocidade num único frame."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.ball_motion import BallMotionAnalyzer
from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.context import AnalyzerContext
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, ShotAnalysisResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.vector import Vector, angle_between


@dataclass
class ShotAnalyzerContext(AnalyzerContext):
    """Memória interna do `ShotAnalyzer` entre chamadas sucessivas de
    `analyze()` - por quantos frames consecutivos os critérios
    instantâneos de chute (velocidade + direção) vêm sendo satisfeitos,
    e em qual frame essa sequência começou. Pertence ao Job - nunca
    sobrevive entre Jobs (`reset()`)."""

    qualifying_streak_frames: int = 0
    streak_start_frame: int | None = None

    def reset(self) -> None:
        self.qualifying_streak_frames = 0
        self.streak_start_frame = None


class ShotAnalyzer(Analyzer):
    """Responde apenas: "houve um evento compatível com um chute?".
    Critérios totalmente determinísticos e parametrizáveis
    (`WORKER_SHOT_MIN_SPEED`/`WORKER_SHOT_MAX_ANGLE_DEVIATION_DEGREES`/
    `WORKER_SHOT_MIN_CONSECUTIVE_FRAMES`) - nenhuma IA, nenhum modelo
    treinado, nenhuma heurística opaca."""

    name = "shot"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._ball_motion_analyzer = BallMotionAnalyzer(settings)
        self._ball_position_analyzer = BallPositionAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._min_speed = settings.shot_min_speed
        self._max_angle_deviation_degrees = settings.shot_max_angle_deviation_degrees
        self._min_consecutive_frames = settings.shot_min_consecutive_frames
        self._context = ShotAnalyzerContext()

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        ball_motion = self._ball_motion_analyzer.analyze(football_world)
        ball_position = self._ball_position_analyzer.analyze(football_world)
        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)

        ball_detected = ball_motion.ball_detected
        motion_detected = ball_motion.motion_detected
        ball_speed = ball_motion.speed
        direction_vector = ball_motion.direction_vector
        direction_angle = ball_motion.direction_angle
        distance_to_goal = ball_position.distance_to_goal_center

        towards_goal = self._towards_goal(
            ball_motion.direction_vector, ball_motion.current_position, goal_geometry.goal_center,
        )

        meets_instant_criteria = (
            bool(motion_detected)
            and ball_speed is not None and ball_speed >= self._min_speed
            and towards_goal is True
        )

        if meets_instant_criteria:
            if self._context.qualifying_streak_frames == 0:
                self._context.streak_start_frame = football_world.frame_index
            self._context.qualifying_streak_frames += 1
        else:
            self._context.qualifying_streak_frames = 0
            self._context.streak_start_frame = None

        shot_detected = (
            meets_instant_criteria
            and self._context.qualifying_streak_frames >= self._min_consecutive_frames
        )
        shot_start_frame = self._context.streak_start_frame if shot_detected else None

        confidence = None
        if ball_motion.confidence is not None and ball_position.confidence is not None:
            confidence = min(ball_motion.confidence, ball_position.confidence)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return ShotAnalysisResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            ball_detected=ball_detected,
            motion_detected=motion_detected,
            shot_detected=shot_detected,
            shot_start_frame=shot_start_frame,
            ball_speed=ball_speed,
            direction_vector=direction_vector,
            direction_angle=direction_angle,
            towards_goal=towards_goal,
            distance_to_goal=distance_to_goal,
            observation_count=ball_motion.frames_observed,
            confidence=confidence,
        )

    def _towards_goal(
        self, direction_vector: Vector | None, current_position: Coordinate | None,
        goal_center: Coordinate | None,
    ) -> bool | None:
        """Compara a direção OBSERVADA do movimento contra a direção da
        bola até o centro do gol - geometria pura (`angle_between`),
        nunca uma previsão de para onde a bola vai continuar. `None` se
        faltar qualquer um dos três insumos (sem movimento observado,
        sem bola, ou sem gol)."""
        if direction_vector is None or current_position is None or goal_center is None:
            return None
        vector_to_goal = Vector.between(current_position, goal_center)
        if vector_to_goal.magnitude() == 0.0:
            return None
        deviation = float(angle_between(direction_vector, vector_to_goal))
        return deviation <= self._max_angle_deviation_degrees

    def reset(self) -> None:
        """Limpa a sequência qualificante interna e delega aos três
        Analyzers compostos - `BallMotionAnalyzer` (genuinamente
        stateful) precisa do reset tanto quanto este; os outros dois são
        hoje um no-op, mas chamados por completude (mesmo princípio já
        aplicado por `BallMotionAnalyzer.reset()`, W18)."""
        self._context.reset()
        self._ball_motion_analyzer.reset()
        self._ball_position_analyzer.reset()
        self._goal_geometry_analyzer.reset()
