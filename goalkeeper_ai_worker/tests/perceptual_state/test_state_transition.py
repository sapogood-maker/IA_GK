"""Testes de worker.perceptual_state.state_transition.StateTransition."""
from __future__ import annotations

import dataclasses

import pytest

from worker.perceptual_state.state_transition import StateTransition


def test_is_frozen_immutable():
    transition = StateTransition(
        dimension="motion", from_state="moving", to_state="stopped", frame_index=10, timestamp_seconds=1.0
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        transition.to_state = "moving"  # type: ignore[misc]


def test_to_dict_contains_all_fields():
    transition = StateTransition(
        dimension="motion", from_state="moving", to_state="stopped", frame_index=10, timestamp_seconds=1.0
    )
    assert transition.to_dict() == {
        "dimension": "motion",
        "from_state": "moving",
        "to_state": "stopped",
        "frame_index": 10,
        "timestamp_seconds": 1.0,
    }
