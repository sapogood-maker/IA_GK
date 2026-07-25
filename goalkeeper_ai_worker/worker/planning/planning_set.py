"""PlanningSet: raiz do conjunto de planos possíveis (Sprint W36) - um
por chamada de `build_plans`.

Dict chaveado por `plan_id` (não tupla) - cada track/entidade tem, no
máximo, um plano por `PlanType` (mapeamento 1:1 com `hypothesis_type`,
já único por track/entidade em `ConvictionSet`)."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.planning.entity_plan import EntityPlan
from worker.planning.track_plan import TrackPlan


@dataclass(frozen=True)
class PlanningSet:
    track_plans: dict[str, TrackPlan] = field(default_factory=dict)
    entity_plans: dict[str, EntityPlan] = field(default_factory=dict)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None

    def to_dict(self) -> dict:
        return {
            "track_plans": {pid: self.track_plans[pid].to_dict() for pid in sorted(self.track_plans)},
            "entity_plans": {pid: self.entity_plans[pid].to_dict() for pid in sorted(self.entity_plans)},
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
        }
