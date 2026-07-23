"""BallPositionAnalyzer: mede a relação geométrica entre a bola e o gol
(Sprint W16). Nenhuma análise de chute, nenhuma previsão de trajetória,
nenhuma avaliação de decisão do goleiro - só mede.

Segue exatamente o padrão de composição introduzido na W15: instancia
`GoalGeometryAnalyzer` internamente e chama `.analyze(football_world)`
como função pura - nenhum canal de comunicação especial entre Analyzers,
nenhuma mudança em `AnalyzerProcessor`/`ProcessorContext`."""
from __future__ import annotations

import time

from worker.analyzers.base import Analyzer
from worker.analyzers.field_areas import estimate_goal_and_penalty_areas
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, BallPositionResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, GoalZone
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector


class BallPositionAnalyzer(Analyzer):
    """Mede: onde está a bola? onde está o gol? qual a relação
    geométrica entre ambas (distância, deslocamento lateral/em
    profundidade, ângulo, dentro de área de meta/pênalti, qual zona do
    gol - se alguma - a posição da bola intercepta)? Nenhuma previsão de
    trajetória, nenhuma avaliação de risco, nenhum conceito de "bola
    perigosa"."""

    name = "ball_position"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._geometry_analyzer = GoalGeometryAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        goal_geometry = self._geometry_analyzer.analyze(football_world)
        balls = football_world.balls
        ball_detected = len(balls) > 0
        goal_detected = goal_geometry.goal_detected

        if not ball_detected or not goal_detected:
            return self._partial_result(
                football_world.frame_index, start, ball_detected, goal_detected, balls, goal_geometry,
            )

        ball = balls[0]
        goal_region = football_world.goals[0].region
        field_region = football_world.field.region

        distance_to_goal_center = float(distance(ball.position, goal_geometry.goal_center))
        lateral_offset = ball.position.y - goal_geometry.goal_center.y
        depth_offset = ball.position.x - goal_geometry.goal_center.x
        angle_to_goal = float(Vector.between(ball.position, goal_geometry.goal_center).angle_degrees())

        goal_area, penalty_area = estimate_goal_and_penalty_areas(goal_region, field_region)
        inside_goal_area = goal_area.contains(ball.position)
        inside_penalty_area = penalty_area.contains(ball.position)

        ball_region = self._locate_zone(goal_geometry.goal_regions, ball.position)

        confidence = min(ball.confidence, goal_geometry.confidence)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return BallPositionResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            ball_detected=True,
            goal_detected=True,
            ball_position=ball.position,
            ball_bbox=ball.bbox,
            distance_to_goal_center=distance_to_goal_center,
            lateral_offset=lateral_offset,
            depth_offset=depth_offset,
            angle_to_goal=angle_to_goal,
            inside_goal_area=inside_goal_area,
            inside_penalty_area=inside_penalty_area,
            ball_region=ball_region,
            goal_center=goal_geometry.goal_center,
            confidence=confidence,
        )

    def _partial_result(
        self, frame_index, start, ball_detected, goal_detected, balls, goal_geometry
    ) -> BallPositionResult:
        """Falta bola OU gol - toda medida que dependeria dos dois é
        explicitamente None, nunca inventada. Os campos que dependem de
        só um lado (ball_position/ball_bbox/goal_center) são preenchidos
        quando esse lado está disponível."""
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        ball = balls[0] if ball_detected else None
        return BallPositionResult(
            frame_index=frame_index,
            metadata=metadata,
            ball_detected=ball_detected,
            goal_detected=goal_detected,
            ball_position=ball.position if ball is not None else None,
            ball_bbox=ball.bbox if ball is not None else None,
            distance_to_goal_center=None,
            lateral_offset=None,
            depth_offset=None,
            angle_to_goal=None,
            inside_goal_area=None,
            inside_penalty_area=None,
            ball_region=None,
            goal_center=goal_geometry.goal_center if goal_detected else None,
            confidence=None,
        )

    @staticmethod
    def _locate_zone(
        goal_regions: dict[GoalZone, Region] | None, ball_position: Coordinate
    ) -> GoalZone | None:
        """Qual zona da grade 2x3 do gol (GoalGeometryAnalyzer, W14)
        contém a posição atual da bola - containment puramente
        geométrico, nunca uma previsão de para onde a bola vai. `None`
        se não houver zonas (geometria degenerada) ou se a bola estiver
        fora de todas (o caso comum, ja que a bola normalmente esta longe
        da faixa fina do gol)."""
        if goal_regions is None:
            return None
        for zone, region in goal_regions.items():
            if region.contains(ball_position):
                return zone
        return None
