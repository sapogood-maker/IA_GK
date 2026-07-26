"""TrackDecision: o resultado da escolha entre os planos possíveis de
UM track_id (Sprint W37).

`plan_type` é copiado do plano vencedor só como FATO informativo (qual
tipo venceu) - nunca usado como entrada de priorização (isso violaria a
genericidade da camada, ver documento arquitetural da W37). Sem campo
de estado próprio (`PlanState` não é reaproveitado, e não há
`DecisionState` paralelo) - `winning_criteria` já representa,
estruturadamente, o resultado do processo de escolha. Nunca contém
Execution/Command/avaliação/texto livre."""
from __future__ import annotations

from dataclasses import dataclass

from worker.planning.plan_type import PlanType


@dataclass(frozen=True)
class TrackDecision:
    track_id: int
    selected_plan_id: str
    plan_type: PlanType
    winning_criteria: tuple[str, ...]
    discarded_plan_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "selected_plan_id": self.selected_plan_id,
            "plan_type": self.plan_type.value,
            "winning_criteria": list(self.winning_criteria),
            "discarded_plan_ids": list(self.discarded_plan_ids),
        }
