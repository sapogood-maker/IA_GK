"""Testes de worker.inference.world.motion.compute_motion - apenas
matematica, nenhuma interpretacao."""
from __future__ import annotations

import pytest

from worker.inference.world.motion import compute_motion
from worker.inference.world.types import Motion, Position


def test_no_previous_position_yields_zeroed_motion() -> None:
    motion = compute_motion(None, Position(x=10, y=10), None)

    assert motion == Motion(displacement=0.0, speed=0.0, direction_degrees=0.0, acceleration=0.0)


def test_horizontal_displacement_computes_speed_and_direction() -> None:
    motion = compute_motion(Position(x=0, y=0), Position(x=10, y=0), None)

    assert motion.displacement == pytest.approx(10.0)
    assert motion.speed == pytest.approx(10.0)
    assert motion.direction_degrees == pytest.approx(0.0)


def test_vertical_displacement_computes_90_degrees() -> None:
    motion = compute_motion(Position(x=0, y=0), Position(x=0, y=10), None)

    assert motion.direction_degrees == pytest.approx(90.0)


def test_diagonal_displacement_computes_expected_speed() -> None:
    motion = compute_motion(Position(x=0, y=0), Position(x=3, y=4), None)

    assert motion.speed == pytest.approx(5.0)  # 3-4-5 triangle


def test_acceleration_reflects_change_in_speed() -> None:
    previous_motion = Motion(displacement=10.0, speed=10.0, direction_degrees=0.0, acceleration=0.0)

    motion = compute_motion(Position(x=10, y=0), Position(x=25, y=0), previous_motion)

    assert motion.speed == pytest.approx(15.0)
    assert motion.acceleration == pytest.approx(5.0)  # 15 - 10


def test_deceleration_yields_negative_acceleration() -> None:
    previous_motion = Motion(displacement=10.0, speed=10.0, direction_degrees=0.0, acceleration=0.0)

    motion = compute_motion(Position(x=10, y=0), Position(x=13, y=0), previous_motion)

    assert motion.speed == pytest.approx(3.0)
    assert motion.acceleration == pytest.approx(-7.0)  # 3 - 10
