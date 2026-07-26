"""DecisionSet: raiz do conjunto de decisões (Sprint W37) - um por
chamada de `decide`.

Chaveado por `track_id`/`entity` diretamente (não por uma string
`decision_id` nova) - mesma convenção de
`WorkingState.track_states`/`entity_states`: já existe exatamente UMA
decisão por sujeito, então o identificador natural já é o próprio
sujeito."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.decision.entity_decision import EntityDecision
from worker.decision.track_decision import TrackDecision


@dataclass(frozen=True)
class DecisionSet:
    track_decisions: dict[int, TrackDecision] = field(default_factory=dict)
    entity_decisions: dict[str, EntityDecision] = field(default_factory=dict)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None

    def to_dict(self) -> dict:
        return {
            "track_decisions": {
                track_id: self.track_decisions[track_id].to_dict() for track_id in sorted(self.track_decisions)
            },
            "entity_decisions": {
                entity: self.entity_decisions[entity].to_dict() for entity in sorted(self.entity_decisions)
            },
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
        }
