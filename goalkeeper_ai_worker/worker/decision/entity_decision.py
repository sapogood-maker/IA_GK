"""EntityDecision: o resultado da escolha entre os planos possíveis de
UMA entidade (Sprint W37).

Irmã de `TrackDecision`, não subclasse - mesma decisão de W33-W36 para
os pares Track/Entity anteriores.

Contrato de campos (decisão arquitetural da Sprint W38): `entity`,
`plan_type` e `winning_criteria` compõem o contrato ESTÁVEL esperado
para consumidores externos ao núcleo. `selected_plan_id`/
`discarded_plan_ids` são registro de AUDITORIA do processo de decisão -
ver a nota equivalente em `track_decision.py`."""
from __future__ import annotations

from dataclasses import dataclass

from worker.planning.plan_type import PlanType


@dataclass(frozen=True)
class EntityDecision:
    entity: str
    selected_plan_id: str
    plan_type: PlanType
    winning_criteria: tuple[str, ...]
    discarded_plan_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "selected_plan_id": self.selected_plan_id,
            "plan_type": self.plan_type.value,
            "winning_criteria": list(self.winning_criteria),
            "discarded_plan_ids": list(self.discarded_plan_ids),
        }
