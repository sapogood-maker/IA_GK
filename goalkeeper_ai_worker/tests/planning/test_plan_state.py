"""Testes de worker.planning.plan_state.PlanState."""
from __future__ import annotations

from worker.planning.plan_state import PlanState


def test_has_exactly_three_values():
    assert {s.value for s in PlanState} == {"emerged", "ongoing", "invalidated"}


def test_never_has_an_abandoned_value():
    """Abandonado nunca e um valor armazenado - representado por
    ausencia do plan_id no PlanningSet seguinte."""
    values = {s.value for s in PlanState}
    assert "abandoned" not in values
    assert "removed" not in values
