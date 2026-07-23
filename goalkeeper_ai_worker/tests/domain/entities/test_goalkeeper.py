"""Testes de worker.domain.entities.goalkeeper.Goalkeeper."""
from __future__ import annotations

from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def test_goalkeeper_to_dict_serializes_all_fields() -> None:
    goalkeeper = Goalkeeper(
        track_id=EntityId(1), label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
        position=Coordinate(x=10, y=20), previous_position=Coordinate(x=5, y=20),
        velocity=Vector(dx=5, dy=0), speed=5.0, bbox=Region(x=0, y=10, width=20, height=40),
        age=3, frames_visible=3, frames_hidden=0, active=True,
    )

    payload = goalkeeper.to_dict()

    assert payload["track_id"] == 1
    assert payload["label"] == "goalkeeper"
    assert payload["position"] == {"x": 10, "y": 20}
    assert payload["previous_position"] == {"x": 5, "y": 20}
    assert payload["velocity"] == {"dx": 5, "dy": 0}
    assert payload["speed"] == 5.0
    assert payload["bbox"] == {"x": 0, "y": 10, "width": 20, "height": 40}
    assert payload["age"] == 3
    assert payload["active"] is True


def test_goalkeeper_without_previous_position() -> None:
    goalkeeper = Goalkeeper(
        track_id=EntityId(1), label=ClassLabel("goalkeeper"), confidence=Confidence(0.9),
        position=Coordinate(x=10, y=20), previous_position=None,
        velocity=Vector(dx=0, dy=0), speed=0.0, bbox=Region(x=0, y=10, width=20, height=40),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )

    assert goalkeeper.to_dict()["previous_position"] is None
