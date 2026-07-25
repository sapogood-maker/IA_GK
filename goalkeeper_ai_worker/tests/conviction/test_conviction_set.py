"""Testes de worker.conviction.conviction_set.ConvictionSet."""
from __future__ import annotations

import dataclasses

import pytest

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_set import ConvictionSet
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.track_conviction import TrackConviction
from worker.hypothesis.hypothesis_type import HypothesisType


def _track_conviction(hypothesis_id: str, track_id: int) -> TrackConviction:
    return TrackConviction(
        hypothesis_id=hypothesis_id,
        hypothesis_type=HypothesisType.STATIONARY,
        track_id=track_id,
        consecutive_observations=1,
        lifetime_observations=1,
        missed_observations=0,
        first_observed_at_frame=0,
        first_observed_at_timestamp=0.0,
        persistence_duration_seconds=0.0,
        state=ConvictionState.BORN,
        level=ConvictionLevel.EMERGING,
    )


def test_is_frozen_immutable():
    conviction_set = ConvictionSet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        conviction_set.observed_at_frame = 99  # type: ignore[misc]


def test_defaults_produce_empty_set_not_errors():
    payload = ConvictionSet().to_dict()
    assert payload["track_convictions"] == {}
    assert payload["entity_convictions"] == {}


def test_to_dict_sorts_track_convictions_by_hypothesis_id():
    conviction_set = ConvictionSet(
        track_convictions={
            "stationary:track:3": _track_conviction("stationary:track:3", 3),
            "stationary:track:1": _track_conviction("stationary:track:1", 1),
        }
    )
    keys = list(conviction_set.to_dict()["track_convictions"].keys())
    assert keys == ["stationary:track:1", "stationary:track:3"]
