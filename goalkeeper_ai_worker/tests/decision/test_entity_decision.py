"""Testes de worker.decision.entity_decision.EntityDecision."""
from __future__ import annotations

import dataclasses

import pytest

from worker.decision.entity_decision import EntityDecision
from worker.planning.plan_type import PlanType


def _make(**overrides) -> EntityDecision:
    defaults = dict(
        entity="ball",
        selected_plan_id="disengage:entity:ball",
        plan_type=PlanType.DISENGAGE,
        winning_criteria=("only_candidate",),
        discarded_plan_ids=(),
    )
    defaults.update(overrides)
    return EntityDecision(**defaults)


def test_is_frozen_immutable():
    decision = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.selected_plan_id = "other"  # type: ignore[misc]


def test_to_dict_serializes_enum():
    payload = _make().to_dict()
    assert payload["plan_type"] == "disengage"
    assert payload["entity"] == "ball"


def test_never_has_execution_or_plan_state_fields():
    field_names = {f.name for f in dataclasses.fields(EntityDecision)}
    forbidden_substrings = ("execution", "command", "recommend", "action", "state")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
