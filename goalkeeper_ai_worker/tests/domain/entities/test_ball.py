"""Testes de worker.domain.entities.ball.Ball."""
from __future__ import annotations

from worker.domain.entities.ball import Ball
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def test_ball_to_dict() -> None:
    ball = Ball(
        track_id=EntityId(3), label=ClassLabel("sports ball"), confidence=Confidence(0.7),
        position=Coordinate(x=50, y=50), previous_position=None,
        velocity=Vector(dx=10, dy=0), speed=10.0, bbox=Region(x=40, y=40, width=20, height=20),
        age=2, frames_visible=2, frames_hidden=0, active=True,
    )

    payload = ball.to_dict()

    assert payload["track_id"] == 3
    assert payload["label"] == "sports ball"
    assert payload["speed"] == 10.0
