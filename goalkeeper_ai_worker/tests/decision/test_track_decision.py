"""Testes de worker.decision.track_decision.TrackDecision."""
from __future__ import annotations

import dataclasses

import pytest

from worker.decision.track_decision import TrackDecision
from worker.planning.plan_type import PlanType


def _make(**overrides) -> TrackDecision:
    defaults = dict(
        track_id=1,
        selected_plan_id="engage:track:1",
        plan_type=PlanType.ENGAGE,
        winning_criteria=("only_candidate",),
        discarded_plan_ids=(),
    )
    defaults.update(overrides)
    return TrackDecision(**defaults)


def test_is_frozen_immutable():
    decision = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.selected_plan_id = "other"  # type: ignore[misc]


def test_to_dict_serializes_enum():
    payload = _make().to_dict()
    assert payload["plan_type"] == "engage"
    assert payload["winning_criteria"] == ["only_candidate"]


def test_never_has_execution_or_plan_state_fields():
    """Reforca os tres ajustes aprovados: nunca Execution/Command/texto
    livre, e nunca um campo 'state'/'plan_state' copiado do plano
    (Decisao e Plano sao conceitos distintos)."""
    field_names = {f.name for f in dataclasses.fields(TrackDecision)}
    forbidden_substrings = ("execution", "command", "recommend", "action", "state")
    assert not any(sub in name for name in field_names for sub in forbidden_substrings)
