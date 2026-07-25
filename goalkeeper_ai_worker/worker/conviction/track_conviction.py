"""TrackConviction: crença sobre a persistência de UMA hipótese de
track ao longo do tempo (Sprint W35).

`hypothesis_id` serve como identificador E referência de origem
(consolidação aprovada - a identidade de uma Conviction é, por
construção, a hipótese que a originou; nunca reconstrói a hipótese em
si). Nunca contém Decision/Action/Recommendation/Coaching/explicação
final - só os fatos de persistência."""
from __future__ import annotations

from dataclasses import dataclass

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_state import ConvictionState
from worker.hypothesis.hypothesis_type import HypothesisType


@dataclass(frozen=True)
class TrackConviction:
    hypothesis_id: str
    hypothesis_type: HypothesisType
    track_id: int
    consecutive_observations: int
    lifetime_observations: int
    missed_observations: int
    first_observed_at_frame: int | None
    first_observed_at_timestamp: float | None
    persistence_duration_seconds: float | None
    state: ConvictionState
    level: ConvictionLevel

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type.value,
            "track_id": self.track_id,
            "consecutive_observations": self.consecutive_observations,
            "lifetime_observations": self.lifetime_observations,
            "missed_observations": self.missed_observations,
            "first_observed_at_frame": self.first_observed_at_frame,
            "first_observed_at_timestamp": self.first_observed_at_timestamp,
            "persistence_duration_seconds": self.persistence_duration_seconds,
            "state": self.state.value,
            "level": self.level.value,
        }
