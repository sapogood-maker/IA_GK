"""GoalkeeperBallAlignmentAnalyzer: primeiro Analyzer RELACIONAL (Sprint
W17) - mede a relação espacial entre goleiro, bola e gol, combinando os
resultados de três Analyzers já existentes. Nenhuma avaliação de
desempenho, nenhum julgamento de posicionamento, nenhuma detecção de
chute, nenhum conceito de "bem posicionado" - só mede.

Segue exatamente o padrão de composição estabelecido nas W14/W15/W16:
instancia `GoalGeometryAnalyzer`/`GoalkeeperPositionAnalyzer`/
`BallPositionAnalyzer` internamente e chama `.analyze(football_world)`
como função pura em cada um - nenhum canal de comunicação especial entre
Analyzers, nenhuma mudança em `AnalyzerProcessor`/`ProcessorContext`.
Combina APENAS os resultados já produzidos por esses três Analyzers -
não reimplementa nenhuma geometria que eles já calculam."""
from __future__ import annotations

import time

from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperBallAlignmentResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.vector import Vector


class GoalkeeperBallAlignmentAnalyzer(Analyzer):
    """Mede a relação espacial entre goleiro, bola e gol: distâncias e
    ângulos par-a-par, e o alinhamento do goleiro com a reta bola→gol
    (distância perpendicular + se a projeção cai dentro do segmento).
    Nenhuma avaliação de qualidade, nenhuma previsão de trajetória."""

    name = "goalkeeper_ball_alignment"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._goal_geometry_analyzer = GoalGeometryAnalyzer(settings)
        self._goalkeeper_position_analyzer = GoalkeeperPositionAnalyzer(settings)
        self._ball_position_analyzer = BallPositionAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        goal_geometry = self._goal_geometry_analyzer.analyze(football_world)
        goalkeeper_result = self._goalkeeper_position_analyzer.analyze(football_world)
        ball_result = self._ball_position_analyzer.analyze(football_world)

        goalkeeper_position = goalkeeper_result.goalkeeper_position
        ball_position = ball_result.ball_position
        goal_center = goal_geometry.goal_center

        goalkeeper_to_ball_distance = None
        goalkeeper_ball_angle = None
        if goalkeeper_position is not None and ball_position is not None:
            goalkeeper_to_ball_distance = float(distance(goalkeeper_position, ball_position))
            goalkeeper_ball_angle = float(
                Vector.between(goalkeeper_position, ball_position).angle_degrees()
            )

        alignment_line = None
        if ball_position is not None and goal_center is not None:
            alignment_line = Vector.between(ball_position, goal_center)

        alignment_offset = None
        is_between_ball_and_goal = None
        if goalkeeper_position is not None and ball_position is not None and goal_center is not None:
            alignment_offset, is_between_ball_and_goal = self._project_onto_line(
                goalkeeper_position, ball_position, goal_center
            )

        confidence = None
        if goalkeeper_result.confidence is not None and ball_result.confidence is not None:
            confidence = min(goalkeeper_result.confidence, ball_result.confidence)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperBallAlignmentResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            goalkeeper_detected=goalkeeper_result.goalkeeper_detected,
            ball_detected=ball_result.ball_detected,
            goal_detected=goal_geometry.goal_detected,
            goalkeeper_position=goalkeeper_position,
            ball_position=ball_position,
            goal_center=goal_center,
            goalkeeper_to_ball_distance=goalkeeper_to_ball_distance,
            ball_to_goal_distance=ball_result.distance_to_goal_center,
            goalkeeper_to_goal_distance=goalkeeper_result.distance_to_goal_center,
            goalkeeper_ball_angle=goalkeeper_ball_angle,
            ball_goal_angle=ball_result.angle_to_goal,
            goalkeeper_goal_angle=goalkeeper_result.angle_to_goal,
            alignment_offset=alignment_offset,
            is_between_ball_and_goal=is_between_ball_and_goal,
            alignment_line=alignment_line,
            confidence=confidence,
        )

    @staticmethod
    def _project_onto_line(
        point: Coordinate, line_start: Coordinate, line_end: Coordinate
    ) -> tuple[float, bool]:
        """Projeta `point` sobre a reta `line_start`->`line_end` -
        devolve a distância perpendicular e se a projeção cai dentro do
        segmento (0 <= t <= 1), não além de nenhuma das extremidades.
        Puramente geométrico - não é uma avaliação de "estar no caminho
        certo", apenas uma medição de posição relativa à reta."""
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            # reta degenerada (bola exatamente no centro do gol) - sem
            # direcao definida, a "distancia perpendicular" vira a
            # distancia direta ao ponto, e "entre" nao se aplica.
            return float(distance(point, line_start)), False

        t = ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / length_squared
        projection = Coordinate(x=line_start.x + t * dx, y=line_start.y + t * dy)
        offset = float(distance(point, projection))
        is_between = 0.0 <= t <= 1.0
        return offset, is_between
