"""Vector: um deslocamento/direção no espaço observado - utilitário puro
de geometria, reutilizado por todos os analisadores futuros de futebol.

Nenhuma interpretação aqui - só matemática (magnitude, ângulo, conversão
polar/cartesiana)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NewType

from worker.domain.geometry.coordinate import Coordinate

Angle = NewType("Angle", float)


@dataclass(frozen=True)
class Vector:
    """Um vetor 2D (dx, dy)."""

    dx: float
    dy: float

    def magnitude(self) -> float:
        return math.hypot(self.dx, self.dy)

    def angle_degrees(self) -> Angle:
        return Angle(math.degrees(math.atan2(self.dy, self.dx)) % 360.0)

    def normalized(self) -> Vector:
        magnitude = self.magnitude()
        if magnitude == 0.0:
            return Vector(dx=0.0, dy=0.0)
        return Vector(dx=self.dx / magnitude, dy=self.dy / magnitude)

    @classmethod
    def from_polar(cls, magnitude: float, angle_degrees: float) -> Vector:
        """Constrói um Vector a partir de magnitude + ângulo (graus) -
        conversão polar para cartesiana, usada para transformar a
        cinemática do World Model (`Motion.speed`/`direction_degrees`)
        em um vetor de velocidade do domínio - só conversão de
        representação, nenhuma interpretação nova."""
        radians = math.radians(angle_degrees)
        return cls(dx=magnitude * math.cos(radians), dy=magnitude * math.sin(radians))

    @classmethod
    def between(cls, origin: Coordinate, target: Coordinate) -> Vector:
        return cls(dx=target.x - origin.x, dy=target.y - origin.y)


def angle_between(a: Vector, b: Vector) -> Angle:
    """Ângulo (em graus, 0-180) entre dois vetores - apenas matemática."""
    magnitude_a, magnitude_b = a.magnitude(), b.magnitude()
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return Angle(0.0)
    dot_product = a.dx * b.dx + a.dy * b.dy
    cosine = max(-1.0, min(1.0, dot_product / (magnitude_a * magnitude_b)))
    return Angle(math.degrees(math.acos(cosine)))
