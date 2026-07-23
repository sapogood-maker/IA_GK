"""Tipos base do Football Domain Model - nunca listas de dicionários
soltos.

`TrackedFootballEntity` é a base compartilhada de `Goalkeeper`/`Ball`/
`Player` (entities/) - os três têm exatamente a mesma forma nesta
sprint (nenhuma regra de futebol os diferencia ainda), mas são classes
DISTINTAS de propósito: analisadores futuros (`GoalkeeperAnalyzer`,
`BallAnalyzer`) devem poder exigir o tipo certo via assinatura, não uma
união genérica."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector

EntityId = NewType("EntityId", int)
ClassLabel = NewType("ClassLabel", str)
Confidence = NewType("Confidence", float)


@dataclass
class TrackedFootballEntity:
    """Estado completo de uma entidade rastreada do domínio de futebol -
    conversão 1:1 dos dados já computados por `ObjectState` (Seção 6.1),
    apenas trocando de representação (Position → Coordinate, Motion →
    Vector, BoundingBox → Region) - nenhum dado novo é inferido aqui.

    `bbox` (Sprint W13): reaproveita `Region` (já existente para
    Field/Goal, Seção 6.4) em vez de introduzir um tipo `BoundingBox`
    próprio do domínio - uma caixa delimitadora É um retângulo, mesma
    forma que uma região de campo/gol. Adicionado nesta sprint porque
    `GoalkeeperPresenceAnalyzer` (Seção 6.5) precisa responder "qual o
    bounding box atual?", e `FootballWorld`/entidades não carregavam essa
    informação até a W12 (só `position`, o centro) - mesma classe de
    achado necessário do `SceneObjectSnapshot` da W11: uma extensão
    aditiva do contrato de uma camada inferior para que a camada de cima
    (aqui, o Analyzer) possa responder à pergunta sem violar o Boundary
    Enforcement (Analyzer só conhece FootballWorld, nunca ObjectState)."""

    track_id: EntityId
    label: ClassLabel
    confidence: Confidence
    position: Coordinate
    previous_position: Coordinate | None
    velocity: Vector
    speed: float
    bbox: Region
    age: int
    frames_visible: int
    frames_hidden: int
    active: bool

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence": self.confidence,
            "position": {"x": self.position.x, "y": self.position.y},
            "previous_position": (
                {"x": self.previous_position.x, "y": self.previous_position.y}
                if self.previous_position is not None
                else None
            ),
            "velocity": {"dx": self.velocity.dx, "dy": self.velocity.dy},
            "speed": self.speed,
            "bbox": self.bbox.to_dict(),
            "age": self.age,
            "frames_visible": self.frames_visible,
            "frames_hidden": self.frames_hidden,
            "active": self.active,
        }
