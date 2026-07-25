"""TrackMemory: projecao agregada do historico de UM track_id (Sprint W32).

So dados - nenhuma logica de agregacao aqui (isso vive em builder.py).
Responde perguntas de HISTORICO ("ha quanto tempo parado", "quantas
transicoes"), nunca de interpretacao ("o goleiro hesitou")."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.memory.event_reference import EventReference


@dataclass(frozen=True)
class TrackMemory:
    track_id: int
    entity: str | None
    first_seen_frame: int
    first_seen_timestamp: float | None
    last_seen_frame: int
    last_seen_timestamp: float | None
    age_seconds: float | None
    current_motion_state: str | None
    motion_state_durations: dict[str, float] = field(default_factory=dict)
    states_visited: tuple[str, ...] = ()
    motion_transition_count: int = 0
    recovery_count: int = 0
    last_change_frame: int | None = None
    last_change_timestamp: float | None = None
    last_relevant_event: EventReference | None = None

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "entity": self.entity,
            "first_seen_frame": self.first_seen_frame,
            "first_seen_timestamp": self.first_seen_timestamp,
            "last_seen_frame": self.last_seen_frame,
            "last_seen_timestamp": self.last_seen_timestamp,
            "age_seconds": self.age_seconds,
            "current_motion_state": self.current_motion_state,
            "motion_state_durations": dict(sorted(self.motion_state_durations.items())),
            "states_visited": list(self.states_visited),
            "motion_transition_count": self.motion_transition_count,
            "recovery_count": self.recovery_count,
            "last_change_frame": self.last_change_frame,
            "last_change_timestamp": self.last_change_timestamp,
            "last_relevant_event": self.last_relevant_event.to_dict() if self.last_relevant_event else None,
        }
