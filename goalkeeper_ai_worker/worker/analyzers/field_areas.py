"""Utilitário geométrico compartilhado entre Analyzers que precisam
estimar retângulos de área de meta/pênalti a partir da geometria do gol
- extraído de `GoalkeeperPositionAnalyzer` (W15) para reuso por
`BallPositionAnalyzer` (W16), evitando duplicar a mesma derivação de
proporções oficiais de campo em dois arquivos. Puramente geométrico -
nenhuma heurística, nenhuma avaliação."""
from __future__ import annotations

from worker.domain.geometry.region import Region

# Proporcoes oficiais de campo de futebol (profundidade / largura da area,
# expressas como multiplos do vao do gol - "goal_height" em GoalGeometryResult),
# mesma disciplina de proporcao fixa e documentada ja usada por
# Goal.default_pair() (W12) - nao sao medidas do video real.
_GOAL_AREA_DEPTH_RATIO = 0.75
_GOAL_AREA_WIDTH_RATIO = 2.5
_PENALTY_AREA_DEPTH_RATIO = 2.25
_PENALTY_AREA_WIDTH_RATIO = 5.5


def estimate_goal_and_penalty_areas(goal_region: Region, field_region: Region) -> tuple[Region, Region]:
    """Deriva retângulos de área de meta/pênalti a partir de proporções
    oficiais fixas (ver módulo) aplicadas ao vão do gol - nunca medidas
    do vídeo real. A direção de extensão (para dentro do campo) é
    decidida comparando a posição do gol contra o centro do campo -
    puramente estrutural, não uma inferência sobre qual lado o goleiro
    defende ou para onde a bola se move."""
    goal_mouth = goal_region.height
    is_left_goal = goal_region.x <= field_region.x + field_region.width / 2
    inner_edge_x = goal_region.x + goal_region.width if is_left_goal else goal_region.x
    center_y = goal_region.center.y

    goal_area_depth = goal_mouth * _GOAL_AREA_DEPTH_RATIO
    goal_area_width = goal_mouth * _GOAL_AREA_WIDTH_RATIO
    penalty_area_depth = goal_mouth * _PENALTY_AREA_DEPTH_RATIO
    penalty_area_width = goal_mouth * _PENALTY_AREA_WIDTH_RATIO

    goal_area_x = inner_edge_x if is_left_goal else inner_edge_x - goal_area_depth
    penalty_area_x = inner_edge_x if is_left_goal else inner_edge_x - penalty_area_depth

    goal_area = Region(
        x=goal_area_x, y=center_y - goal_area_width / 2,
        width=goal_area_depth, height=goal_area_width,
    )
    penalty_area = Region(
        x=penalty_area_x, y=center_y - penalty_area_width / 2,
        width=penalty_area_depth, height=penalty_area_width,
    )
    return goal_area, penalty_area
