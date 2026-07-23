"""Region: uma área retangular do espaço observado (campo, gol, área
penal, etc.) - utilitário puro de geometria."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.geometry.coordinate import Coordinate


@dataclass(frozen=True)
class Region:
    """Um retângulo (x, y, width, height)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Coordinate:
        return Coordinate(x=self.x + self.width / 2, y=self.y + self.height / 2)

    def contains(self, coordinate: Coordinate) -> bool:
        return (
            self.x <= coordinate.x <= self.x + self.width
            and self.y <= coordinate.y <= self.y + self.height
        )

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}
