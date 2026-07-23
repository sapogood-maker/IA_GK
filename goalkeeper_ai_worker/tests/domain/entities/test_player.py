"""Testes de worker.domain.entities.player.Player."""
from __future__ import annotations

from worker.domain.entities.player import Player
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def test_player_to_dict() -> None:
    player = Player(
        track_id=EntityId(2), label=ClassLabel("person"), confidence=Confidence(0.85),
        position=Coordinate(x=1, y=1), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=0, y=0, width=10, height=20),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )

    payload = player.to_dict()

    assert payload["track_id"] == 2
    assert payload["label"] == "person"
