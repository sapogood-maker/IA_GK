"""Testes de worker.domain.geometry.coordinate."""
from __future__ import annotations

import pytest

from worker.domain.geometry.coordinate import Coordinate, distance


def test_distance_between_same_point_is_zero() -> None:
    assert distance(Coordinate(1, 1), Coordinate(1, 1)) == 0.0


def test_distance_horizontal() -> None:
    assert distance(Coordinate(0, 0), Coordinate(10, 0)) == pytest.approx(10.0)


def test_distance_3_4_5_triangle() -> None:
    assert distance(Coordinate(0, 0), Coordinate(3, 4)) == pytest.approx(5.0)
