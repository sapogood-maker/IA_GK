"""Rule Evaluation: mecanismo genérico e reutilizável de avaliação de
regras determinísticas, explicáveis e auditáveis (Sprint W23) - primeira
peça da camada de Explainability do Worker.

Nenhuma regra vive aqui - este módulo só define o CONTRATO (`Rule`,
`RuleOutcome`, `evaluate_rules`), reutilizável por qualquer Analyzer de
avaliação futuro (não só `GoalkeeperDecisionEvaluationAnalyzer`). Cada
`Rule.condition` é uma função PURA de um contexto arbitrário para:

- `True` — a regra foi SATISFEITA;
- `False` — a regra foi VIOLADA;
- `None` — a regra NÃO É APLICÁVEL a este caso (não conta como sucesso
  nem como falha - ex.: uma regra sobre mergulho não se aplica a um
  frame em que o goleiro não mergulhou).

`evaluate_rules()` nunca descarta, reordena ou resume uma regra
silenciosamente - cada `Rule` produz exatamente um `RuleOutcome`,
sempre com `rule_id`/descrição/resultado/explicação textual. Nenhuma
regra "vence" silenciosamente sobre outra - a agregação num veredito
final (ex.: `GoalkeeperDecisionEvaluation`) é responsabilidade de quem
chama `evaluate_rules()`, nunca deste módulo genérico."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Rule(Generic[T]):
    """Uma regra determinística nomeada e documentada.

    `id` identifica a regra de forma estável (usado em `rules_evaluated`/
    `rules_passed`/`rules_failed` do resultado que a consome - nunca
    reaproveitar um `id` para uma regra com semântica diferente).
    `description` é a justificativa textual, sempre presente na
    explicação do `RuleOutcome` correspondente - nenhuma regra sem
    documentação. `condition` é a única lógica real - uma função pura,
    sem efeito colateral, sem I/O, sem estado."""

    id: str
    description: str
    condition: Callable[[T], bool | None]


@dataclass(frozen=True)
class RuleOutcome:
    """Resultado de UMA regra avaliada - sempre rastreável até
    `rule_id`, sempre acompanhado de uma `explanation` textual (nunca um
    veredito sem justificativa)."""

    rule_id: str
    description: str
    passed: bool | None
    explanation: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "passed": self.passed,
            "explanation": self.explanation,
        }


def evaluate_rules(rules: list[Rule[T]], context: T) -> list[RuleOutcome]:
    """Aplica cada regra ao `context`, na MESMA ordem da lista -
    devolve exatamente um `RuleOutcome` por `Rule`, nunca menos."""
    outcomes = []
    for rule in rules:
        passed = rule.condition(context)
        if passed is True:
            verdict = "satisfeita"
        elif passed is False:
            verdict = "violada"
        else:
            verdict = "nao aplicavel"
        outcomes.append(RuleOutcome(
            rule_id=rule.id,
            description=rule.description,
            passed=passed,
            explanation=f"[{rule.id}] {rule.description} -> {verdict}",
        ))
    return outcomes
