"""Testes de worker.planning.plan_type.PlanType."""
from __future__ import annotations

from worker.planning.plan_type import PlanType


def test_has_exactly_four_values():
    assert {t.value for t in PlanType} == {"engage", "pursue", "reacquire", "disengage"}


def test_never_has_domain_specific_names():
    """Ajuste aprovado: nunca usar taticas especificas de dominio
    (futebol/goleiro) como approach/intercept."""
    values = {t.value for t in PlanType}
    assert "approach" not in values
    assert "intercept" not in values


def test_never_has_a_trajectory_value():
    assert "trajectory" not in {t.value for t in PlanType}
