"""GoalGeometryAnalyzer: primeiro Analyzer geométrico (Sprint W14) -
modela a geometria do gol (centro, postes, dimensões, regiões/zonas de
cobertura). Nenhuma avaliação de goleiro, defesa, chute, mergulho ou
reação - puramente geométrico e determinístico, igual em espírito ao
`GoalkeeperPresenceAnalyzer` (W13)."""
from __future__ import annotations

import time

from worker.analyzers.base import Analyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalGeometryResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion, GoalZone
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region

_ZONE_ROWS = ("top", "bottom")
_ZONE_COLUMNS = ("left", "center", "right")


class GoalGeometryAnalyzer(Analyzer):
    """Responde: o gol foi detectado (existe no FootballWorld)? qual o
    centro/largura/altura/postes de referência? quais as regiões/zonas de
    cobertura do gol?

    Quando `FootballWorld.goals` tem mais de um candidato (o Football
    Domain Model, W12, sempre cria os dois gols do campo), esta
    implementação escolhe deterministicamente o PRIMEIRO da lista - mesma
    regra de ordem já usada por `GoalkeeperPresenceAnalyzer` (W13), não
    uma heurística sobre qual gol é "o relevante" (isso dependeria de
    saber de que lado o goleiro está - fora de escopo desta sprint,
    puramente geométrica)."""

    name = "goal_geometry"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        """Não usa nenhum campo de `settings` hoje - mantém a assinatura
        uniforme já usada por toda implementação concreta desde a W4."""

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()
        goals = football_world.goals

        if not goals:
            return self._empty_result(football_world.frame_index, start)

        region = goals[0].region
        is_well_formed = region.width > 0 and region.height > 0

        left_post = Coordinate(x=region.x, y=region.y)
        right_post = Coordinate(x=region.x + region.width, y=region.y)
        goal_regions = self._compute_zones(region) if is_well_formed else None
        confidence = 1.0 if is_well_formed else 0.0

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalGeometryResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            goal_detected=True,
            goal_center=region.center,
            goal_width=region.width,
            goal_height=region.height,
            left_post=left_post,
            right_post=right_post,
            goal_regions=goal_regions,
            confidence=confidence,
        )

    def _empty_result(self, frame_index: int, start: float) -> GoalGeometryResult:
        """Nenhum gol no FootballWorld - retorna "desconhecido" de forma
        explícita em todo campo geométrico, nunca inventa valores."""
        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalGeometryResult(
            frame_index=frame_index,
            metadata=metadata,
            goal_detected=False,
            goal_center=None,
            goal_width=None,
            goal_height=None,
            left_post=None,
            right_post=None,
            goal_regions=None,
            confidence=None,
        )

    @staticmethod
    def _compute_zones(region: Region) -> dict[GoalZone, Region]:
        """Divide a região do gol numa grade 2x3 (2 linhas: topo/base; 3
        colunas: esquerda/centro/direita) - só aritmética, nenhuma
        interpretação de qual zona é "melhor" ou "pior"."""
        column_width = region.width / len(_ZONE_COLUMNS)
        row_height = region.height / len(_ZONE_ROWS)

        zones: dict[GoalZone, Region] = {}
        for row_index, row_name in enumerate(_ZONE_ROWS):
            for column_index, column_name in enumerate(_ZONE_COLUMNS):
                zone = GoalZone(f"{row_name}_{column_name}")
                zones[zone] = Region(
                    x=region.x + column_index * column_width,
                    y=region.y + row_index * row_height,
                    width=column_width,
                    height=row_height,
                )
        return zones
