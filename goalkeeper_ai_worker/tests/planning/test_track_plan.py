"""Testes de worker.planning.track_plan.TrackPlan."""
from __future__ import annotations

import dataclasses

import pytest

from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.track_plan import TrackPlan


def _make(**overrides) -> TrackPlan:
    defaults = dict(
        plan_id="engage:track:1",
        plan_type=PlanType.ENGAGE,
        track_id=1,
        origin_conviction_id="stationary:track:1",
        satisfied_preconditions=("conviction_level_at_least_stable",),
        state=PlanState.EMERGED,
        objective="Um plano de engajamento passa a ser possível para o track 1.",
    )
    defaults.update(overrides)
    return TrackPlan(**defaults)


def test_is_frozen_immutable():
    plan = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.state = PlanState.ONGOING  # type: ignore[misc]


def test_to_dict_serializes_enums():
    payload = _make().to_dict()
    assert payload["plan_type"] == "engage"
    assert payload["state"] == "emerged"
    assert payload["satisfied_preconditions"] == ["conviction_level_at_least_stable"]


def test_never_has_decision_or_action_fields():
    field_names = {f.name for f in dataclasses.fields(TrackPlan)}
    forbidden_substrings = ("decision", "command", "recommend", "action", "execution")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
