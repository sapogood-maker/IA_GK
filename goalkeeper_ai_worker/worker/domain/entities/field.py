"""Field: o campo/quadra - entidade estática representando a região de
jogo e a direção de ataque. Nenhuma lógica de posição tática vive aqui."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.geometry.direction import Direction
from worker.domain.geometry.region import Region


@dataclass
class Field:
    """O campo - região de jogo + direção de ataque conhecida."""

    region: Region
    direction: Direction

    def to_dict(self) -> dict:
        return {"region": self.region.to_dict(), "direction": self.direction.value}

    @classmethod
    def default(cls) -> "Field":
        """Geometria placeholder normalizada (0.0-1.0 em ambos os eixos)
        - documentada honestamente: sem informação de câmera/marcações do
        campo disponível nesta camada (Seção 6.1 da Constituição), esta
        NÃO é a geometria real do vídeo processado. `direction` também é
        sempre `UNKNOWN` por padrão - nenhuma heurística tenta inferir a
        direção de ataque nesta sprint."""
        return cls(region=Region(x=0.0, y=0.0, width=1.0, height=1.0), direction=Direction.UNKNOWN)
