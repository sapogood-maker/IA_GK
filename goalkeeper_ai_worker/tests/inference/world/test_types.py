"""Testes de worker.inference.world.types."""
from __future__ import annotations

from worker.inference.world.types import Motion


def test_motion_to_dict_serializes_all_fields() -> None:
    motion = Motion(displacement=5.0, speed=5.0, direction_degrees=90.0, acceleration=1.5)

    assert motion.to_dict() == {
        "displacement": 5.0, "speed": 5.0, "direction_degrees": 90.0, "acceleration": 1.5,
    }
