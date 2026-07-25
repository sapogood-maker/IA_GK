"""Testes de worker.hypothesis.entity_hypothesis.EntityHypothesis."""
from __future__ import annotations

import dataclasses

import pytest

from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType


def _make(**overrides) -> EntityHypothesis:
    defaults = dict(
        hypothesis_id="visibility:entity:ball",
        hypothesis_type=HypothesisType.VISIBILITY,
        entity="ball",
        description="A entidade 'ball' aparenta estar deixando a cena.",
        evidence=(Evidence("active_track_ids", "0"),),
        matching_conditions=("no_active_tracks",),
        support=1,
        origin="visibility_entity",
    )
    defaults.update(overrides)
    return EntityHypothesis(**defaults)


def test_is_frozen_immutable():
    hyp = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        hyp.support = 99  # type: ignore[misc]


def test_to_dict_serializes_enum_and_evidence():
    payload = _make().to_dict()
    assert payload["hypothesis_type"] == "visibility"
    assert payload["entity"] == "ball"
    assert payload["evidence"] == [{"field": "active_track_ids", "value": "0"}]


def test_never_has_a_confidence_field():
    field_names = {f.name for f in dataclasses.fields(EntityHypothesis)}
    assert not any("confidence" in name for name in field_names)
