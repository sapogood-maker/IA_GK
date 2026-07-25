"""Testes de worker.planning.entity_plan.EntityPlan."""
from __future__ import annotations

import dataclasses

import pytest

from worker.planning.entity_plan import EntityPlan
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType


def _make(**overrides) -> EntityPlan:
    defaults = dict(
        plan_id="disengage:entity:ball",
        plan_type=PlanType.DISENGAGE,
        entity="ball",
        origin_conviction_id="visibility:entity:ball",
        satisfied_preconditions=("conviction_level_at_least_stable",),
        state=PlanState.EMERGED,
        objective="Um plano de desengajamento passa a ser possível para a entidade 'ball'.",
    )
    defaults.update(overrides)
    return EntityPlan(**defaults)


def test_is_frozen_immutable():
    plan = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.state = PlanState.ONGOING  # type: ignore[misc]


def test_to_dict_serializes_enums():
    payload = _make().to_dict()
    assert payload["plan_type"] == "disengage"
    assert payload["entity"] == "ball"


def test_never_has_decision_or_action_fields():
    field_names = {f.name for f in dataclasses.fields(EntityPlan)}
    forbidden_substrings = ("decision", "command", "recommend", "action", "execution")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
