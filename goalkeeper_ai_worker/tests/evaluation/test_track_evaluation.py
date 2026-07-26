"""Testes de worker.evaluation.track_evaluation.TrackEvaluation."""
from __future__ import annotations

import dataclasses

import pytest

from worker.evaluation.resolution_method import ResolutionMethod
from worker.evaluation.track_evaluation import TrackEvaluation


def _make(**overrides) -> TrackEvaluation:
    defaults = dict(track_id=1, resolution_method=ResolutionMethod.SINGLE_CANDIDATE)
    defaults.update(overrides)
    return TrackEvaluation(**defaults)


def test_is_frozen_immutable():
    evaluation = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        evaluation.resolution_method = ResolutionMethod.STRUCTURAL_CRITERION  # type: ignore[misc]


def test_to_dict_serializes_enum():
    payload = _make().to_dict()
    assert payload["resolution_method"] == "single_candidate"


def test_never_has_result_environment_or_copied_decision_fields():
    """Reforca os ajustes aprovados: nunca campo de avaliacao de
    resultado/ambiente/execucao, e nunca winning_criteria/
    selected_plan_id/discarded_plan_ids copiados de TrackDecision."""
    field_names = {f.name for f in dataclasses.fields(TrackEvaluation)}
    forbidden_substrings = (
        "result",
        "environment",
        "execution",
        "winning_criteria",
        "selected_plan_id",
        "discarded_plan_ids",
    )
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
