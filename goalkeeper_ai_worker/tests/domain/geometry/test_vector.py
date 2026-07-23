"""Testes de worker.domain.geometry.vector."""
from __future__ import annotations

import pytest

from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.vector import Vector, angle_between


def test_magnitude() -> None:
    assert Vector(dx=3, dy=4).magnitude() == pytest.approx(5.0)


def test_angle_degrees_pointing_right() -> None:
    assert Vector(dx=1, dy=0).angle_degrees() == pytest.approx(0.0)


def test_angle_degrees_pointing_down() -> None:
    assert Vector(dx=0, dy=1).angle_degrees() == pytest.approx(90.0)


def test_normalized_has_unit_magnitude() -> None:
    normalized = Vector(dx=3, dy=4).normalized()
    assert normalized.magnitude() == pytest.approx(1.0)


def test_normalized_zero_vector_stays_zero() -> None:
    assert Vector(dx=0, dy=0).normalized() == Vector(dx=0.0, dy=0.0)


def test_from_polar_reconstructs_expected_vector() -> None:
    vector = Vector.from_polar(magnitude=10.0, angle_degrees=0.0)
    assert vector.dx == pytest.approx(10.0)
    assert vector.dy == pytest.approx(0.0)


def test_between_computes_displacement() -> None:
    vector = Vector.between(Coordinate(0, 0), Coordinate(3, 4))
    assert vector.dx == pytest.approx(3.0)
    assert vector.dy == pytest.approx(4.0)


def test_angle_between_parallel_vectors_is_zero() -> None:
    assert angle_between(Vector(1, 0), Vector(2, 0)) == pytest.approx(0.0)


def test_angle_between_perpendicular_vectors_is_90() -> None:
    assert angle_between(Vector(1, 0), Vector(0, 1)) == pytest.approx(90.0)


def test_angle_between_opposite_vectors_is_180() -> None:
    assert angle_between(Vector(1, 0), Vector(-1, 0)) == pytest.approx(180.0)


def test_angle_between_zero_vector_is_zero() -> None:
    assert angle_between(Vector(0, 0), Vector(1, 0)) == 0.0
