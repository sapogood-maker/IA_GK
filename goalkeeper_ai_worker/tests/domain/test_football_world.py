"""Testes de worker.domain.football_world.FootballWorld."""
from __future__ import annotations

from worker.domain.entities.ball import Ball
from worker.domain.entities.player import Player
from worker.domain.football_world import FootballWorld
from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region
from worker.domain.geometry.vector import Vector
from worker.domain.types import ClassLabel, Confidence, EntityId


def _player() -> Player:
    return Player(
        track_id=EntityId(1), label=ClassLabel("person"), confidence=Confidence(0.9),
        position=Coordinate(x=0, y=0), previous_position=None,
        velocity=Vector(0, 0), speed=0.0, bbox=Region(x=0, y=0, width=10, height=20),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _ball() -> Ball:
    return Ball(
        track_id=EntityId(2), label=ClassLabel("sports ball"), confidence=Confidence(0.7),
        position=Coordinate(x=1, y=1), previous_position=None,
        velocity=Vector(0, 0), speed=0.0, bbox=Region(x=1, y=1, width=5, height=5),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def test_default_world_is_empty_but_has_a_field() -> None:
    world = FootballWorld()

    assert world.goalkeepers == []
    assert world.players == []
    assert world.balls == []
    assert world.field is not None


def test_to_dict_serializes_all_entity_groups() -> None:
    world = FootballWorld(frame_index=5, players=[_player()], balls=[_ball()])

    payload = world.to_dict()

    assert payload["frame_index"] == 5
    assert len(payload["players"]) == 1
    assert len(payload["balls"]) == 1
    assert payload["goalkeepers"] == []
    assert "field" in payload
