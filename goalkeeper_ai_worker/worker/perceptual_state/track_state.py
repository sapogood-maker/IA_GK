"""TrackState: representação do estado atual observado de UM track_id
(Sprint W33).

So representacao - nenhum campo de validacao (isso vive em
transition_validation.py, responsabilidade separada de proposito). Nao
julga: so diz o que É, ha quanto tempo, e qual foi a ultima mudanca."""
from __future__ import annotations

from dataclasses import dataclass

from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.state_transition import StateTransition


@dataclass(frozen=True)
class TrackState:
    track_id: int
    entity: str | None
    motion_state: MotionState
    motion_state_since_timestamp: float | None
    motion_state_duration_seconds: float | None
    motion_transition_count: int
    last_motion_transition: StateTransition | None
    presence_state: PresenceState
    time_since_last_seen_seconds: float | None
    presence_transition: StateTransition | None
    recovery_count: int

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "entity": self.entity,
            "motion_state": self.motion_state.value,
            "motion_state_since_timestamp": self.motion_state_since_timestamp,
            "motion_state_duration_seconds": self.motion_state_duration_seconds,
            "motion_transition_count": self.motion_transition_count,
            "last_motion_transition": self.last_motion_transition.to_dict() if self.last_motion_transition else None,
            "presence_state": self.presence_state.value,
            "time_since_last_seen_seconds": self.time_since_last_seen_seconds,
            "presence_transition": self.presence_transition.to_dict() if self.presence_transition else None,
            "recovery_count": self.recovery_count,
        }
