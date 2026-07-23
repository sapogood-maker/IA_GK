"""GoalkeeperPositionAnalyzer: primeiro Analyzer que mede a relação
geométrica entre goleiro e gol (Sprint W15). Nenhuma avaliação de
qualidade, nenhum julgamento de "posição correta" - só mede.

Segue o padrão oficial de composição entre Analyzers definido na W14
(Seção 6.5/16 da Constituição): instancia `GoalGeometryAnalyzer`
internamente e chama `.analyze(football_world)` como função pura -
nenhum canal de comunicação especial entre Analyzers, nenhuma mudança em
`AnalyzerProcessor`/`ProcessorContext`."""
from __future__ import annotations

import time

from worker.analyzers.base import Analyzer
from worker.analyzers.field_areas import estimate_goal_and_penalty_areas
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperPositionResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate, distance
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector


class GoalkeeperPositionAnalyzer(Analyzer):
    """Mede: onde está o goleiro? onde está o gol? qual a relação
    geométrica entre ambos (distância, deslocamento lateral/em
    profundidade, ângulo, dentro de área de meta/pênalti, alinhamento com
    os terços do gol)? Nenhuma avaliação de qualidade nem julgamento de
    posicionamento correto."""

    name = "goalkeeper_position"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._geometry_analyzer = GoalGeometryAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        goal_geometry = self._geometry_analyzer.analyze(football_world)
        goalkeepers = football_world.goalkeepers
        goalkeeper_detected = len(goalkeepers) > 0
        goal_detected = goal_geometry.goal_detected

        if not goalkeeper_detected or not goal_detected:
            return self._partial_result(
                football_world.frame_index, start, goalkeeper_detected, goal_detected,
                goalkeepers, goal_geometry,
            )

        goalkeeper = goalkeepers[0]
        goal_region = football_world.goals[0].region
        field_region = football_world.field.region

        distance_to_goal_center = float(distance(goalkeeper.position, goal_geometry.goal_center))
        lateral_offset = goalkeeper.position.y - goal_geometry.goal_center.y
        depth_offset = goalkeeper.position.x - goal_geometry.goal_center.x
        angle_to_goal = float(Vector.between(goalkeeper.position, goal_geometry.goal_center).angle_degrees())

        goal_area, penalty_area = estimate_goal_and_penalty_areas(goal_region, field_region)
        inside_goal_area = goal_area.contains(goalkeeper.position)
        inside_penalty_area = penalty_area.contains(goalkeeper.position)

        covers_left_post, covers_center, covers_right_post = self._covers_thirds(
            goal_region, goalkeeper.position
        )

        confidence = min(goalkeeper.confidence, goal_geometry.confidence)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperPositionResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            goalkeeper_detected=True,
            goal_detected=True,
            distance_to_goal_center=distance_to_goal_center,
            lateral_offset=lateral_offset,
            depth_offset=depth_offset,
            angle_to_goal=angle_to_goal,
            inside_goal_area=inside_goal_area,
            inside_penalty_area=inside_penalty_area,
            covers_left_post=covers_left_post,
            covers_center=covers_center,
            covers_right_post=covers_right_post,
            goalkeeper_position=goalkeeper.position,
            goal_center=goal_geometry.goal_center,
            confidence=confidence,
        )

    def _partial_result(
        self, frame_index, start, goalkeeper_detected, goal_detected, goalkeepers, goal_geometry
    ) -> GoalkeeperPositionResult:
        """Falta goleiro OU gol - toda medida que dependeria dos dois é
        explicitamente None, nunca inventada. Os campos que dependem de
        só um lado (goalkeeper_position/goal_center) são preenchidos
        quando esse lado está disponível."""
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperPositionResult(
            frame_index=frame_index,
            metadata=metadata,
            goalkeeper_detected=goalkeeper_detected,
            goal_detected=goal_detected,
            distance_to_goal_center=None,
            lateral_offset=None,
            depth_offset=None,
            angle_to_goal=None,
            inside_goal_area=None,
            inside_penalty_area=None,
            covers_left_post=None,
            covers_center=None,
            covers_right_post=None,
            goalkeeper_position=goalkeepers[0].position if goalkeeper_detected else None,
            goal_center=goal_geometry.goal_center if goal_detected else None,
            confidence=None,
        )

    @staticmethod
    def _covers_thirds(goal_region: Region, goalkeeper_position: Coordinate) -> tuple[bool, bool, bool]:
        """Divide o vão do gol em 3 terços iguais ao longo do eixo y -
        convenção determinística de que y menor corresponde ao poste
        esquerdo (sem calibração de câmera/direção conhecida, arbitrária
        mas fixa). Apenas um terço é True (a posição lateral do goleiro
        cai exatamente num deles)."""
        third = goal_region.height / 3
        left_bound = goal_region.y + third
        right_bound = goal_region.y + 2 * third
        gk_y = goalkeeper_position.y

        covers_left_post = gk_y < left_bound
        covers_center = left_bound <= gk_y < right_bound
        covers_right_post = gk_y >= right_bound
        return covers_left_post, covers_center, covers_right_post
