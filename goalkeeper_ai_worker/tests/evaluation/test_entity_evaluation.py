"""Testes de worker.evaluation.entity_evaluation.EntityEvaluation."""
from __future__ import annotations

import dataclasses

import pytest

from worker.evaluation.entity_evaluation import EntityEvaluation
from worker.evaluation.resolution_method import ResolutionMethod


def _make(**overrides) -> EntityEvaluation:
    defaults = dict(entity="ball", resolution_method=ResolutionMethod.SINGLE_CANDIDATE)
    defaults.update(overrides)
    return EntityEvaluation(**defaults)


def test_is_frozen_immutable():
    evaluation = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        evaluation.resolution_method = ResolutionMethod.STRUCTURAL_CRITERION  # type: ignore[misc]


def test_to_dict_serializes_enum():
    payload = _make().to_dict()
    assert payload["resolution_method"] == "single_candidate"
    assert payload["entity"] == "ball"


def test_never_has_result_environment_or_copied_decision_fields():
    field_names = {f.name for f in dataclasses.fields(EntityEvaluation)}
    forbidden_substrings = (
        "result",
        "environment",
        "execution",
        "winning_criteria",
        "selected_plan_id",
        "discarded_plan_ids",
    )
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
