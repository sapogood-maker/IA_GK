"""Testes de worker.domain.geometry.direction."""
from __future__ import annotations

from worker.domain.geometry.direction import Direction


def test_direction_has_three_values() -> None:
    assert Direction.LEFT_TO_RIGHT.value == "left_to_right"
    assert Direction.RIGHT_TO_LEFT.value == "right_to_left"
    assert Direction.UNKNOWN.value == "unknown"
