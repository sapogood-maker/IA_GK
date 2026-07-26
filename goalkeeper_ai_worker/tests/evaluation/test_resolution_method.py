"""Testes de worker.evaluation.resolution_method.ResolutionMethod."""
from __future__ import annotations

from worker.evaluation.resolution_method import ResolutionMethod


def test_has_exactly_three_values():
    assert {m.value for m in ResolutionMethod} == {
        "single_candidate",
        "structural_criterion",
        "deterministic_tiebreak",
    }


def test_never_has_judgment_values():
    """ResolutionMethod nunca julga qualidade - so o mecanismo
    estrutural. Nunca 'good'/'bad'/'correct', nunca a palavra 'rule'
    (Rule Engine excluido do nucleo desde W31/W36)."""
    values = {m.value for m in ResolutionMethod}
    assert not any(word in v for v in values for word in ("good", "bad", "correct", "rule"))
