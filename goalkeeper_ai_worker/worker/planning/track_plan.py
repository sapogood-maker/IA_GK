"""TrackPlan: um plano possível para UM track_id (Sprint W36).

`origin_conviction_id` referencia explicitamente a Conviction que
originou o plano (o mesmo `hypothesis_id` usado como chave em
`ConvictionSet.track_convictions`) - nunca reconstrói a Conviction ou a
Hypothesis em si. Nunca contém Decision/Command/Recommendation/Action/
Execution - só os fatos de possibilidade."""
from __future__ import annotations

from dataclasses import dataclass

from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType


@dataclass(frozen=True)
class TrackPlan:
    plan_id: str
    plan_type: PlanType
    track_id: int
    origin_conviction_id: str
    satisfied_preconditions: tuple[str, ...]
    state: PlanState
    objective: str

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "plan_type": self.plan_type.value,
            "track_id": self.track_id,
            "origin_conviction_id": self.origin_conviction_id,
            "satisfied_preconditions": list(self.satisfied_preconditions),
            "state": self.state.value,
            "objective": self.objective,
        }
