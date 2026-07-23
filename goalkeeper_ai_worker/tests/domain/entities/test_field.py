"""Testes de worker.domain.entities.field.Field."""
from __future__ import annotations

from worker.domain.entities.field import Field
from worker.domain.geometry.direction import Direction


def test_default_field_is_normalized_and_unknown_direction() -> None:
    field = Field.default()

    assert field.region.width == 1.0
    assert field.region.height == 1.0
    assert field.direction == Direction.UNKNOWN


def test_field_to_dict() -> None:
    field = Field.default()
    payload = field.to_dict()

    assert payload["direction"] == "unknown"
    assert payload["region"] == {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
