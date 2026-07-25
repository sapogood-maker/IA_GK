"""EntityMemory: projecao agregada do historico de TODOS os track_id sob
o mesmo rotulo normalizado (Sprint W32) - ex. "ball".

Existe porque o Tracker cria um track_id NOVO a cada reaquisicao apos
oclusao/perda - "a bola" fisicamente e uma so, mas pode ter passado por
varios track_id diferentes. EntityMemory responde "ha quanto tempo ESTE
ROTULO existe no video", nao "ha quanto tempo este track_id existe"
(isso e TrackMemory)."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.memory.event_reference import EventReference


@dataclass(frozen=True)
class EntityMemory:
    entity: str
    track_ids: frozenset[int]
    first_seen_timestamp: float | None
    last_seen_timestamp: float | None
    combined_motion_state_durations: dict[str, float] = field(default_factory=dict)
    total_recovery_count: int = 0
    last_relevant_event: EventReference | None = None

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "track_ids": sorted(self.track_ids),
            "first_seen_timestamp": self.first_seen_timestamp,
            "last_seen_timestamp": self.last_seen_timestamp,
            "combined_motion_state_durations": dict(sorted(self.combined_motion_state_durations.items())),
            "total_recovery_count": self.total_recovery_count,
            "last_relevant_event": self.last_relevant_event.to_dict() if self.last_relevant_event else None,
        }
