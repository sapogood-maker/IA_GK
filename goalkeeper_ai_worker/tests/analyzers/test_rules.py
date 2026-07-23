"""Testes de worker.analyzers.rules - mecanismo generico de Rule
Evaluation (Sprint W23): Rule/RuleOutcome/evaluate_rules. Nao pertence a
nenhum Analyzer especifico - testado isoladamente aqui."""
from __future__ import annotations

from worker.analyzers.rules import Rule, RuleOutcome, evaluate_rules


def test_evaluate_rules_produces_one_outcome_per_rule_in_order() -> None:
    rules = [
        Rule("always_true", "Sempre satisfeita", lambda ctx: True),
        Rule("always_false", "Sempre violada", lambda ctx: False),
        Rule("not_applicable", "Nunca aplicavel", lambda ctx: None),
    ]

    outcomes = evaluate_rules(rules, context={})

    assert [outcome.rule_id for outcome in outcomes] == ["always_true", "always_false", "not_applicable"]
    assert [outcome.passed for outcome in outcomes] == [True, False, None]


def test_rule_outcome_explanation_reflects_verdict() -> None:
    rules = [
        Rule("r1", "Descricao da regra", lambda ctx: True),
        Rule("r2", "Descricao da regra", lambda ctx: False),
        Rule("r3", "Descricao da regra", lambda ctx: None),
    ]

    outcomes = evaluate_rules(rules, context={})

    assert "satisfeita" in outcomes[0].explanation
    assert "violada" in outcomes[1].explanation
    assert "nao aplicavel" in outcomes[2].explanation
    assert all(outcome.description == "Descricao da regra" for outcome in outcomes)


def test_rule_condition_receives_the_context() -> None:
    rule = Rule("uses_context", "Le o contexto", lambda ctx: ctx["value"] > 10)

    outcomes = evaluate_rules([rule], context={"value": 20})
    assert outcomes[0].passed is True

    outcomes = evaluate_rules([rule], context={"value": 5})
    assert outcomes[0].passed is False


def test_rule_outcome_to_dict() -> None:
    outcome = RuleOutcome(rule_id="r1", description="desc", passed=True, explanation="[r1] desc -> satisfeita")

    assert outcome.to_dict() == {
        "rule_id": "r1", "description": "desc", "passed": True, "explanation": "[r1] desc -> satisfeita",
    }


def test_evaluate_rules_with_empty_list_returns_empty() -> None:
    assert evaluate_rules([], context={}) == []
