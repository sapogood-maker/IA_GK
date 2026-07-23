"""Testes de worker.domain.geometry.region."""
from __future__ import annotations

from worker.domain.geometry.coordinate import Coordinate
from worker.domain.geometry.region import Region


def test_center_of_region() -> None:
    region = Region(x=0, y=0, width=10, height=20)
    assert region.center == Coordinate(x=5, y=10)


def test_contains_point_inside() -> None:
    region = Region(x=0, y=0, width=10, height=10)
    assert region.contains(Coordinate(5, 5)) is True


def test_contains_point_outside() -> None:
    region = Region(x=0, y=0, width=10, height=10)
    assert region.contains(Coordinate(20, 20)) is False


def test_contains_point_on_boundary() -> None:
    region = Region(x=0, y=0, width=10, height=10)
    assert region.contains(Coordinate(10, 10)) is True


def test_to_dict() -> None:
    region = Region(x=1, y=2, width=3, height=4)
    assert region.to_dict() == {"x": 1, "y": 2, "width": 3, "height": 4}
