"""Testes de worker.planning.planning_set.PlanningSet."""
from __future__ import annotations

import dataclasses

import pytest

from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan


def _track_plan(track_id: int) -> TrackPlan:
    return TrackPlan(
        plan_id=f"engage:track:{track_id}",
        plan_type=PlanType.ENGAGE,
        track_id=track_id,
        origin_conviction_id=f"stationary:track:{track_id}",
        satisfied_preconditions=("conviction_level_at_least_stable",),
        state=PlanState.EMERGED,
        objective="...",
    )


def test_is_frozen_immutable():
    planning_set = PlanningSet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        planning_set.observed_at_frame = 99  # type: ignore[misc]


def test_defaults_produce_empty_set_not_errors():
    payload = PlanningSet().to_dict()
    assert payload["track_plans"] == {}
    assert payload["entity_plans"] == {}


def test_to_dict_sorts_track_plans_by_plan_id():
    planning_set = PlanningSet(
        track_plans={"engage:track:3": _track_plan(3), "engage:track:1": _track_plan(1)}
    )
    keys = list(planning_set.to_dict()["track_plans"].keys())
    assert keys == ["engage:track:1", "engage:track:3"]
