"""EntityPlan: um plano possível para UMA entidade (Sprint W36).

Irmã de `TrackPlan`, não subclasse - mesma decisão de W33-W35 para os
pares Track/Entity anteriores."""
from __future__ import annotations

from dataclasses import dataclass

from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType


@dataclass(frozen=True)
class EntityPlan:
    plan_id: str
    plan_type: PlanType
    entity: str
    origin_conviction_id: str
    satisfied_preconditions: tuple[str, ...]
    state: PlanState
    objective: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "plan_type": self.plan_type.value,
            "entity": self.entity,
            "origin_conviction_id": self.origin_conviction_id,
            "satisfied_preconditions": list(self.satisfied_preconditions),
            "state": self.state.value,
            "objective": self.objective,
        }
