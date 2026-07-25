"""Testes de worker.hypothesis.hypothesis_type.HypothesisType."""
from __future__ import annotations

from worker.hypothesis.hypothesis_type import HypothesisType


def test_has_exactly_four_values():
    assert {t.value for t in HypothesisType} == {"stationary", "movement", "recovery", "visibility"}


def test_never_has_a_trajectory_value():
    """WorkingState nao carrega posicao/direcao - TrajectoryHypothesis
    foi deliberadamente descartada (documento arquitetural, Secao 3)."""
    assert "trajectory" not in {t.value for t in HypothesisType}
