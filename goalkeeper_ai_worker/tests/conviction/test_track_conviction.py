"""Testes de worker.conviction.track_conviction.TrackConviction."""
from __future__ import annotations

import dataclasses

import pytest

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.track_conviction import TrackConviction
from worker.hypothesis.hypothesis_type import HypothesisType


def _make(**overrides) -> TrackConviction:
    defaults = dict(
        hypothesis_id="stationary:track:1",
        hypothesis_type=HypothesisType.STATIONARY,
        track_id=1,
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
    return TrackConviction(**defaults)


def test_is_frozen_immutable():
    conviction = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        conviction.consecutive_observations = 99  # type: ignore[misc]


def test_to_dict_serializes_enums():
    payload = _make().to_dict()
    assert payload["hypothesis_type"] == "stationary"
    assert payload["state"] == "born"
    assert payload["level"] == "emerging"


def test_never_has_decision_or_action_fields():
    """Reforca a separacao de responsabilidades: Conviction nunca
    contem Decision/Action/Recommendation/Coaching/explicacao final."""
    field_names = {f.name for f in dataclasses.fields(TrackConviction)}
    forbidden_substrings = ("decision", "action", "recommend", "coach", "explanation", "confidence")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
