"""Coordinate: um ponto no espaço observado (pixels ou normalizado,
dependendo de quem o produz) - utilitário puro de geometria, reutilizado
por todos os analisadores futuros de futebol."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NewType

Distance = NewType("Distance", float)


@dataclass(frozen=True)
class Coordinate:
    """Um ponto (x, y)."""

    x: float
    y: float


def distance(a: Coordinate, b: Coordinate) -> Distance:
    """Distância euclidiana entre dois pontos - apenas matemática."""
    return Distance(math.hypot(b.x - a.x, b.y - a.y))
