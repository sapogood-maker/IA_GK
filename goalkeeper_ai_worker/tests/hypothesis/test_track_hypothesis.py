"""Testes de worker.hypothesis.track_hypothesis.TrackHypothesis."""
from __future__ import annotations

import dataclasses

import pytest

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis


def _make(**overrides) -> TrackHypothesis:
    defaults = dict(
        hypothesis_id="stationary:track:1",
        hypothesis_type=HypothesisType.STATIONARY,
        track_id=1,
        description="O objeto no track 1 aparenta estar parado.",
        evidence=(Evidence("motion_state", "stopped"),),
        matching_conditions=("motion_state_is_stopped",),
        support=1,
        origin="stationary",
    )
    defaults.update(overrides)
    return TrackHypothesis(**defaults)


def test_is_frozen_immutable():
    hyp = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        hyp.support = 99  # type: ignore[misc]


def test_to_dict_serializes_enum_and_evidence():
    hyp = _make()
    payload = hyp.to_dict()
    assert payload["hypothesis_type"] == "stationary"
    assert payload["evidence"] == [{"field": "motion_state", "value": "stopped"}]
    assert payload["matching_conditions"] == ["motion_state_is_stopped"]


def test_never_has_a_confidence_field():
    """Reforca o ajuste aprovado: support e uma contagem, nunca uma
    confianca/probabilidade - nenhum campo pode se chamar 'confidence'."""
    field_names = {f.name for f in dataclasses.fields(TrackHypothesis)}
    assert not any("confidence" in name for name in field_names)


def test_origin_is_a_stable_concept_identifier_not_a_function_name():
    """Ajuste aprovado: origin nao pode conter sufixo de nome de funcao
    como '_rule'."""
    hyp = _make()
    assert "_rule" not in hyp.origin
    assert "produce_" not in hyp.origin
