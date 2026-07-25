"""Testes de worker.hypothesis.hypothesis_set.HypothesisSet."""
from __future__ import annotations

import dataclasses

import pytest

from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis


def _track_hyp(track_id: int) -> TrackHypothesis:
    return TrackHypothesis(
        hypothesis_id=f"stationary:track:{track_id}",
        hypothesis_type=HypothesisType.STATIONARY,
        track_id=track_id,
        description="...",
        evidence=(Evidence("motion_state", "stopped"),),
        matching_conditions=("motion_state_is_stopped",),
        support=1,
        origin="stationary",
    )


def _entity_hyp(entity: str) -> EntityHypothesis:
    return EntityHypothesis(
        hypothesis_id=f"visibility:entity:{entity}",
        hypothesis_type=HypothesisType.VISIBILITY,
        entity=entity,
        description="...",
        evidence=(Evidence("active_track_ids", "0"),),
        matching_conditions=("no_active_tracks",),
        support=1,
        origin="visibility_entity",
    )


def test_is_frozen_immutable():
    hyp_set = HypothesisSet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        hyp_set.source_track_count = 99  # type: ignore[misc]


def test_defaults_produce_empty_set_not_errors():
    payload = HypothesisSet().to_dict()
    assert payload["track_hypotheses"] == []
    assert payload["entity_hypotheses"] == []
    assert payload["source_track_count"] == 0


def test_to_dict_sorts_track_hypotheses_by_hypothesis_id():
    hyp_set = HypothesisSet(track_hypotheses=(_track_hyp(3), _track_hyp(1)))
    ids = [h["hypothesis_id"] for h in hyp_set.to_dict()["track_hypotheses"]]
    assert ids == ["stationary:track:1", "stationary:track:3"]


def test_to_dict_sorts_entity_hypotheses_by_hypothesis_id():
    hyp_set = HypothesisSet(entity_hypotheses=(_entity_hyp("person"), _entity_hyp("ball")))
    ids = [h["hypothesis_id"] for h in hyp_set.to_dict()["entity_hypotheses"]]
    assert ids == ["visibility:entity:ball", "visibility:entity:person"]
