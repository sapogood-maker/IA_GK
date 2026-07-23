"""PlaySituationAnalyzer: primeiro Analyzer COGNITIVO (Sprint W21) -
classifica APENAS o estado observado da jogada atual (`PlaySituation`),
combinando exclusivamente resultados já produzidos por quatro Analyzers
existentes. NUNCA avalia o goleiro, NUNCA avalia defesa, NUNCA julga
decisões, NUNCA emite nota de qualidade - é uma CLASSIFICAÇÃO
determinística de um estado observável, não uma opinião.

Segue o padrão de composição estabelecido nas W14-W20: instancia
`ShotAnalyzer`/`BallTrajectoryAnalyzer`/`GoalkeeperBallAlignmentAnalyzer`/
`GoalGeometryAnalyzer` internamente e chama `.analyze(football_world)`
como função pura em cada um - nenhum canal de comunicação especial entre
Analyzers, nenhuma mudança em `AnalyzerProcessor`/`ProcessorContext`.
Nenhuma informação já disponível nesses quatro resultados é recalculada
- `situation`/`sub_state` são só uma árvore de decisão determinística
sobre campos já computados (`ball_detected`/`goalkeeper_detected`/
`shot_detected`/`motion_detected`/`towards_goal`).

Este Analyzer, ao contrário de `ShotAnalyzer`/`BallTrajectoryAnalyzer`,
NÃO é stateful - é um combinador puro (sem `AnalyzerContext` próprio);
o estado que existe pertence inteiramente aos dois Analyzers compostos
que já são stateful (`ShotAnalyzer`/`BallTrajectoryAnalyzer`), cujo
`reset()` é delegado normalmente."""
from __future__ import annotations

import time

from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, PlaySituationResult
from worker.analyzers.shot import ShotAnalyzer
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, PlaySituation
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld


class PlaySituationAnalyzer(Analyzer):
    """Responde apenas: "qual é a situação atual da jogada?" - uma
    classificação determinística, fortemente tipada (`PlaySituation`),
    derivada exclusivamente de sinais já computados por quatro Analyzers
    existentes. Nunca avalia goleiro/defesa, nunca julga decisões, nunca
    emite nota de qualidade."""

    name = "play_situation"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._shot_analyzer = ShotAnalyzer(settings)
        self._ball_trajectory_analyzer = BallTrajectoryAnalyzer(settings)
        self._goalkeeper_ball_alignment_analyzer = GoalkeeperBallAlignmentAnalyzer(settings)
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        shot = self._shot_analyzer.analyze(football_world)
        trajectory = self._ball_trajectory_analyzer.analyze(football_world)
        alignment = self._goalkeeper_ball_alignment_analyzer.analyze(football_world)
        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)

        ball_detected = alignment.ball_detected
        goalkeeper_detected = alignment.goalkeeper_detected
        shot_detected = shot.shot_detected
        trajectory_detected = trajectory.trajectory_detected
        alignment_detected = alignment.alignment_offset is not None

        situation = self._classify(ball_detected, goalkeeper_detected, shot_detected, shot.motion_detected)
        sub_state = self._classify_direction(shot.motion_detected, shot.towards_goal)

        confidence = None
        signals = [shot.confidence, trajectory.confidence, alignment.confidence, goal_geometry.confidence]
        if all(signal is not None for signal in signals):
            confidence = min(signals)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return PlaySituationResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            situation=situation,
            sub_state=sub_state,
            ball_detected=ball_detected,
            goalkeeper_detected=goalkeeper_detected,
            shot_detected=shot_detected,
            trajectory_detected=trajectory_detected,
            alignment_detected=alignment_detected,
            confidence=confidence,
        )

    @staticmethod
    def _classify(
        ball_detected: bool, goalkeeper_detected: bool, shot_detected: bool, motion_detected: bool | None,
    ) -> PlaySituation:
        """Árvore de decisão determinística, por ordem de PRIORIDADE fixa
        - cada regra olha só para sinais já computados por outros
        Analyzers, nunca recalcula nada. Ausência de bola tem prioridade
        sobre ausência de goleiro (sem bola, não há jogada nenhuma para
        classificar); ausência de goleiro tem prioridade sobre chute
        detectado (mesmo que um chute genuíno esteja ocorrendo, a cena
        está incompleta sem o goleiro visível - um caveat mais
        fundamental que a classificação do movimento da bola)."""
        if not ball_detected:
            return PlaySituation.NO_BALL_VISIBLE
        if not goalkeeper_detected:
            return PlaySituation.NO_GOALKEEPER_VISIBLE
        if shot_detected:
            return PlaySituation.SHOT_DETECTED
        if motion_detected is True:
            return PlaySituation.BALL_MOVING
        if motion_detected is False:
            return PlaySituation.BALL_STATIONARY
        return PlaySituation.UNKNOWN

    @staticmethod
    def _classify_direction(motion_detected: bool | None, towards_goal: bool | None) -> PlaySituation | None:
        """Refinamento opcional sobre a direção do movimento observado -
        independente de `shot_detected` já ter sido confirmado (que exige
        velocidade mínima + frames consecutivos, W19); aqui basta que
        haja movimento real (`motion_detected is True`) e uma direção
        observada comparável contra o gol (`towards_goal`, já calculado
        por `ShotAnalyzer` via `angle_between()`, nunca recalculado aqui).

        Exige `motion_detected is True` explicitamente - sem isso,
        `towards_goal` pode ser `True` mesmo para uma bola PARADA (a
        magnitude zero do vetor de direção faz `angle_between()`
        devolver 0° por convenção matemática de vetor degenerado, não por
        haver de fato uma direção "em direção ao gol"). Sem este guard,
        `sub_state=SHOT_TOWARDS_GOAL` apareceria de forma enganosa junto
        de `situation=BALL_STATIONARY`."""
        if motion_detected is not True:
            return None
        if towards_goal is True:
            return PlaySituation.SHOT_TOWARDS_GOAL
        if towards_goal is False:
            return PlaySituation.SHOT_AWAY_FROM_GOAL
        return None

    def reset(self) -> None:
        """Delega `reset()` aos quatro Analyzers compostos - dois deles
        (`ShotAnalyzer`/`BallTrajectoryAnalyzer`) são genuinamente
        STATEFUL; os outros dois são no-op, chamados por completude
        (mesmo princípio já aplicado por `ShotAnalyzer.reset()`, W19)."""
        self._shot_analyzer.reset()
        self._ball_trajectory_analyzer.reset()
        self._goalkeeper_ball_alignment_analyzer.reset()
        self._goal_geometry_analyzer.reset()
