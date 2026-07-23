"""Goal: uma baliza - entidade estática (não rastreada frame a frame),
representada pela região que ocupa no campo. Nenhuma lógica de gol
marcado vive aqui - isso é responsabilidade de um futuro `GoalAnalyzer`
(Seção 16 da Constituição)."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.geometry.region import Region


@dataclass
class Goal:
    """Uma baliza, representada pela sua região no campo."""

    region: Region

    def to_dict(self) -> dict:
        return {"region": self.region.to_dict()}

    @classmethod
    def default_pair(cls, field_region: Region) -> list["Goal"]:
        """Duas balizas nas extremidades esquerda e direita do campo.

        **Geometria placeholder, documentada honestamente**: sem
        calibração de câmera ou marcações reais do campo disponíveis
        nesta camada (Seção 6.1 da Constituição), as dimensões são
        proporções arbitrárias do `field_region` - não a posição real
        das balizas no vídeo. Uma sprint futura de calibração de câmera
        deverá substituir isso por geometria derivada do vídeo real."""
        goal_width = field_region.width * 0.02
        goal_height = field_region.height * 0.3
        goal_y = field_region.y + (field_region.height - goal_height) / 2

        left_goal = cls(region=Region(x=field_region.x, y=goal_y, width=goal_width, height=goal_height))
        right_goal = cls(
            region=Region(
                x=field_region.x + field_region.width - goal_width,
                y=goal_y, width=goal_width, height=goal_height,
            )
        )
        return [left_goal, right_goal]
