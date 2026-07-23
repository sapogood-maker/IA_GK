"""BallMotionAnalyzer: mede o movimento OBSERVADO da bola entre frames
consecutivos (Sprint W18) - primeiro Analyzer STATEFUL da Analyzer API.
Nenhuma previsão de trajetória futura, nenhuma detecção de chute, nenhuma
avaliação de risco/perigo - apenas o que já aconteceu.

Segue o padrão de composição estabelecido nas W14-W17: instancia
`BallPositionAnalyzer` internamente e chama `.analyze(football_world)`
como função pura - nenhum canal de comunicação especial entre Analyzers,
nenhuma mudança em `AnalyzerProcessor`/`ProcessorContext`.

Usa `AnalyzerContext` (reservada desde a W13) pela primeira vez: guarda a
posição/velocidade/track_id da bola do frame anterior para poder medir
deslocamento/velocidade/aceleração no frame atual. `reset()` limpa esse
estado - chamado pela mesma plumbing genérica de `AnalyzerProcessor.
reset()` (Seção 6.1, "Estado entre Jobs") no início de cada Job, sem
nenhuma mudança nela."""
from __future__ import annotations

import time
from dataclasses import dataclass

from worker.analyzers.base import Analyzer
from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.context import AnalyzerContext
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, BallMotionResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.vector import Vector
from worker.domain.types import EntityId


@dataclass
class BallMotionContext(AnalyzerContext):
    """Memória interna do `BallMotionAnalyzer` entre chamadas sucessivas
    de `analyze()` - a posição/velocidade/identidade da bola do frame
    ANTERIOR. Pertence ao Job - nunca sobrevive entre Jobs (`reset()`)."""

    previous_position: Coordinate | None = None
    previous_velocity: Vector | None = None
    previous_track_id: EntityId | None = None
    frames_observed: int = 0

    def reset(self) -> None:
        self.previous_position = None
        self.previous_velocity = None
        self.previous_track_id = None
        self.frames_observed = 0


class BallMotionAnalyzer(Analyzer):
    """Mede: a bola se moveu desde o frame anterior? qual o deslocamento/
    velocidade/direção/aceleração OBSERVADOS? Nunca prevê para onde a
    bola vai, nunca avalia se o movimento é perigoso."""

    name = "ball_motion"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._ball_position_analyzer = BallPositionAnalyzer(settings)
        self._context = BallMotionContext()

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        ball_result = self._ball_position_analyzer.analyze(football_world)

        if not ball_result.ball_detected:
            # Bola sumiu deste frame - a continuidade de observacao esta
            # quebrada. Nunca inferimos deslocamento atraves de uma
            # lacuna de frames onde a bola nao foi vista, entao o
            # estado interno e limpo: um reaparecimento futuro sera
            # tratado como uma primeira observacao nova, nunca como
            # continuacao do movimento anterior.
            self._context.reset()
            return self._result(football_world.frame_index, start, ball_detected=False)

        current_ball = football_world.balls[0]
        current_position = ball_result.ball_position
        current_track_id = current_ball.track_id

        is_same_ball_as_before = (
            self._context.previous_position is not None
            and self._context.previous_track_id == current_track_id
        )

        if not is_same_ball_as_before:
            # Primeira observacao desta bola (ou o track_id mudou desde
            # o ultimo frame - uma identidade DIFERENTE, nao a mesma bola
            # continuando) - nao ha posicao anterior valida para comparar.
            result = self._result(
                football_world.frame_index, start, ball_detected=True,
                current_position=current_position, previous_position=None,
                frames_observed=1, confidence=float(current_ball.confidence),
            )
            self._context.previous_position = current_position
            self._context.previous_velocity = None
            self._context.previous_track_id = current_track_id
            self._context.frames_observed = 1
            return result

        previous_position = self._context.previous_position
        displacement = float(distance(previous_position, current_position))
        velocity = Vector.between(previous_position, current_position)
        speed = velocity.magnitude()
        direction_vector = velocity.normalized()
        direction_angle = float(velocity.angle_degrees())
        motion_detected = displacement > 0.0
        stationary = displacement == 0.0

        acceleration = None
        if self._context.previous_velocity is not None:
            acceleration = speed - self._context.previous_velocity.magnitude()

        frames_observed = self._context.frames_observed + 1

        result = self._result(
            football_world.frame_index, start, ball_detected=True,
            current_position=current_position, previous_position=previous_position,
            displacement=displacement, velocity=velocity, speed=speed,
            direction_vector=direction_vector, direction_angle=direction_angle,
            acceleration=acceleration, frames_observed=frames_observed,
            motion_detected=motion_detected, stationary=stationary,
            confidence=float(current_ball.confidence),
        )

        self._context.previous_position = current_position
        self._context.previous_velocity = velocity
        self._context.previous_track_id = current_track_id
        self._context.frames_observed = frames_observed
        return result

    def _result(
        self, frame_index: int, start: float, *, ball_detected: bool,
        current_position: Coordinate | None = None, previous_position: Coordinate | None = None,
        displacement: float | None = None, velocity: Vector | None = None, speed: float | None = None,
        direction_vector: Vector | None = None, direction_angle: float | None = None,
        acceleration: float | None = None, frames_observed: int = 0,
        motion_detected: bool | None = None, stationary: bool | None = None,
        confidence: float | None = None,
    ) -> BallMotionResult:
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return BallMotionResult(
            frame_index=frame_index,
            metadata=metadata,
            ball_detected=ball_detected,
            current_position=current_position,
            previous_position=previous_position,
            displacement=displacement,
            velocity=velocity,
            speed=speed,
            direction_vector=direction_vector,
            direction_angle=direction_angle,
            acceleration=acceleration,
            frames_observed=frames_observed,
            motion_detected=motion_detected,
            stationary=stationary,
            confidence=confidence,
        )

    def reset(self) -> None:
        """Limpa toda a memoria de movimento acumulada - chamado uma vez
        no inicio de cada Job (Secao 6.1, "Estado entre Jobs"). Sem isso,
        a mesma instancia de BallMotionAnalyzer (reaproveitada entre Jobs
        sequenciais) vazaria posicao/velocidade da bola de um video para
        o proximo, produzindo um deslocamento/aceleracao inventados entre
        dois videos sem nenhuma relacao real."""
        self._context.reset()
        self._ball_position_analyzer.reset()
