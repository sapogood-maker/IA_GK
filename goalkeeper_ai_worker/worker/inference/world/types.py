"""Tipos básicos próprios do World Model - nunca listas de dicionários
soltos.

Deliberadamente independentes dos tipos de `worker.inference.trackers`/
`worker.inference.detectors` (mesmo padrão `BoundingBox`/`ClassLabel`/
`Confidence` já duplicado entre essas duas famílias) - `world/` nunca
importa de `trackers/`/`detectors/`, só de `events/types.py`
(`SceneAnalysisResult`, o único contrato de entrada permitido)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

ObjectId = NewType("ObjectId", int)
ClassLabel = NewType("ClassLabel", str)
Confidence = NewType("Confidence", float)


@dataclass(frozen=True)
class BoundingBox:
    """Caixa delimitadora de um objeto do mundo, em pixels."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Position:
    """Posição do centro de um objeto, em pixels (pode ter fração)."""

    x: float
    y: float


@dataclass(frozen=True)
class Motion:
    """Cinemática pura de um objeto entre dois frames - nenhuma
    interpretação (não classifica "parado"/"em movimento", isso é
    responsabilidade de `SceneAnalyzer`, Seção 6.1)."""

    displacement: float
    speed: float
    direction_degrees: float
    acceleration: float

    def to_dict(self) -> dict:
        return {
            "displacement": self.displacement,
            "speed": self.speed,
            "direction_degrees": self.direction_degrees,
            "acceleration": self.acceleration,
        }
