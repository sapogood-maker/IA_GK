"""Testes de worker.conviction.entity_conviction.EntityConviction."""
from __future__ import annotations

import dataclasses

import pytest

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.entity_conviction import EntityConviction
from worker.hypothesis.hypothesis_type import HypothesisType


def _make(**overrides) -> EntityConviction:
    defaults = dict(
        hypothesis_id="visibility:entity:ball",
        hypothesis_type=HypothesisType.VISIBILITY,
        entity="ball",
        consecutive_observations=1,
        lifetime_observations=1,
        missed_observations=0,
        first_observed_at_frame=100,
        first_observed_at_timestamp=10.0,
        persistence_duration_seconds=0.0,
        state=ConvictionState.BORN,
        level=ConvictionLevel.EMERGING,
    )
    defaults.update(overrides)
    return EntityConviction(**defaults)


def test_is_frozen_immutable():
    conviction = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        conviction.consecutive_observations = 99  # type: ignore[misc]


def test_to_dict_serializes_enums():
    payload = _make().to_dict()
    assert payload["hypothesis_type"] == "visibility"
    assert payload["entity"] == "ball"
    assert payload["state"] == "born"


def test_never_has_decision_or_action_fields():
    field_names = {f.name for f in dataclasses.fields(EntityConviction)}
    forbidden_substrings = ("decision", "action", "recommend", "coach", "explanation", "confidence")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
