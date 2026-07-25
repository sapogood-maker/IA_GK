"""Testes de worker.hypothesis.evidence.Evidence."""
from __future__ import annotations

import dataclasses

import pytest

from worker.hypothesis.evidence import Evidence


def test_is_frozen_immutable():
    evidence = Evidence(field="motion_state", value="stopped")
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.value = "moving"  # type: ignore[misc]


def test_to_dict():
    evidence = Evidence(field="motion_state", value="stopped")
    assert evidence.to_dict() == {"field": "motion_state", "value": "stopped"}
