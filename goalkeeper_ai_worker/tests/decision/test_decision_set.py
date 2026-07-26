"""Testes de worker.decision.decision_set.DecisionSet."""
from __future__ import annotations

import dataclasses

import pytest

from worker.decision.decision_set import DecisionSet
from worker.decision.track_decision import TrackDecision
from worker.planning.plan_type import PlanType


def _track_decision(track_id: int) -> TrackDecision:
    return TrackDecision(
        track_id=track_id,
        selected_plan_id=f"engage:track:{track_id}",
        plan_type=PlanType.ENGAGE,
        winning_criteria=("only_candidate",),
        discarded_plan_ids=(),
    )


def test_is_frozen_immutable():
    decision_set = DecisionSet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision_set.observed_at_frame = 99  # type: ignore[misc]


def test_defaults_produce_empty_set_not_errors():
    payload = DecisionSet().to_dict()
    assert payload["track_decisions"] == {}
    assert payload["entity_decisions"] == {}


def test_to_dict_sorts_track_decisions_by_track_id():
    decision_set = DecisionSet(track_decisions={3: _track_decision(3), 1: _track_decision(1)})
    assert list(decision_set.to_dict()["track_decisions"].keys()) == [1, 3]
