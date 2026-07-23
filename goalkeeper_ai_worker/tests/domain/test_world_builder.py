"""Testes de worker.domain.world_builder.FootballWorldBuilder - usa a
implementacao real (sem mock) contra WorldStates sinteticos."""
from __future__ import annotations

from worker.config.settings import get_settings
from worker.domain.entities.ball import Ball
from worker.domain.entities.goalkeeper import Goalkeeper
from worker.domain.entities.player import Player
from worker.domain.world_builder import FootballWorldBuilder
from worker.inference.world.object_state import ObjectState
from worker.inference.world.types import BoundingBox, ClassLabel, Confidence, Motion, ObjectId, Position
from worker.inference.world.world_state import WorldState


def _object_state(track_id: int, label: str, x: int = 10, y: int = 10,
                   speed: float = 0.0, direction_degrees: float = 0.0) -> ObjectState:
    return ObjectState(
        track_id=ObjectId(track_id), label=ClassLabel(label), confidence=Confidence(0.9),
        bbox=BoundingBox(x=x, y=y, width=20, height=40), previous_bbox=None,
        position=Position(x=x + 10, y=y + 20),
        motion=Motion(displacement=speed, speed=speed, direction_degrees=direction_degrees, acceleration=0.0),
        age=1, frames_visible=1, frames_hidden=0, active=True,
    )


def _world_state(objects: list[ObjectState], frame_index: int = 0) -> WorldState:
    return WorldState(frame_index=frame_index, active_objects=objects)


def test_person_label_becomes_player() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "person")]))

    assert len(world.players) == 1
    assert isinstance(world.players[0], Player)
    assert world.balls == []
    assert world.goalkeepers == []


def test_ball_like_labels_become_ball() -> None:
    builder = FootballWorldBuilder(get_settings())

    for label in ("ball", "sports ball", "frisbee"):
        world = builder.build(_world_state([_object_state(1, label)]))
        assert len(world.balls) == 1
        assert isinstance(world.balls[0], Ball)


def test_goalkeeper_label_becomes_goalkeeper() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "goalkeeper")]))

    assert len(world.goalkeepers) == 1
    assert isinstance(world.goalkeepers[0], Goalkeeper)


def test_unknown_label_is_silently_ignored() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "traffic light")]))

    assert world.players == []
    assert world.balls == []
    assert world.goalkeepers == []


def test_velocity_is_converted_from_polar_motion() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "person", speed=10.0, direction_degrees=0.0)]))

    player = world.players[0]
    assert player.speed == 10.0
    assert player.velocity.dx == 10.0
    assert player.velocity.dy == 0.0


def test_position_matches_object_state_position() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "person", x=5, y=5)]))

    assert world.players[0].position.x == 15  # x + width/2 already applied in ObjectState.position
    assert world.players[0].position.y == 25


def test_bbox_matches_object_state_bbox() -> None:
    builder = FootballWorldBuilder(get_settings())

    world = builder.build(_world_state([_object_state(1, "person", x=5, y=5)]))

    bbox = world.players[0].bbox
    assert (bbox.x, bbox.y, bbox.width, bbox.height) == (5, 5, 20, 40)


def test_field_and_goals_persist_across_calls() -> None:
    builder = FootballWorldBuilder(get_settings())

    world_a = builder.build(_world_state([_object_state(1, "person")], frame_index=0))
    world_b = builder.build(_world_state([_object_state(1, "person")], frame_index=1))

    assert world_a.field is world_b.field
    assert world_a.goals == world_b.goals
    assert len(world_a.goals) == 2


def test_reset_clears_field_and_goals_so_they_are_rebuilt() -> None:
    builder = FootballWorldBuilder(get_settings())
    world_a = builder.build(_world_state([_object_state(1, "person")], frame_index=0))

    builder.reset()
    world_b = builder.build(_world_state([_object_state(1, "person")], frame_index=0))

    assert world_a.field is not world_b.field  # nova instancia apos reset
