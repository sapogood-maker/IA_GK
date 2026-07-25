"""WorkingState: raiz da projeção determinística do estado atual
observado (Sprint W33) - um por chamada de `build_working_state`."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.track_state import TrackState


@dataclass(frozen=True)
class WorkingState:
    track_states: dict[int, TrackState] = field(default_factory=dict)
    entity_states: dict[str, EntityState] = field(default_factory=dict)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None
    source_track_count: int = 0

    def to_dict(self) -> dict:
        return {
            "track_states": {
                track_id: self.track_states[track_id].to_dict() for track_id in sorted(self.track_states)
            },
            "entity_states": {
                entity: self.entity_states[entity].to_dict() for entity in sorted(self.entity_states)
            },
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
            "source_track_count": self.source_track_count,
        }
