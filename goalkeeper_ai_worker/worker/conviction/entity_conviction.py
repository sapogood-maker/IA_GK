"""EntityConviction: crença sobre a persistência de UMA hipótese de
entidade ao longo do tempo (Sprint W35).

Irmã de `TrackConviction`, não subclasse - mesma decisão de W33/W34
para TrackState/EntityState e TrackHypothesis/EntityHypothesis."""
from __future__ import annotations

from dataclasses import dataclass

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_state import ConvictionState
from worker.hypothesis.hypothesis_type import HypothesisType


@dataclass(frozen=True)
class EntityConviction:
    hypothesis_id: str
    hypothesis_type: HypothesisType
    entity: str
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
            "entity": self.entity,
            "consecutive_observations": self.consecutive_observations,
            "lifetime_observations": self.lifetime_observations,
            "missed_observations": self.missed_observations,
            "first_observed_at_frame": self.first_observed_at_frame,
            "first_observed_at_timestamp": self.first_observed_at_timestamp,
            "persistence_duration_seconds": self.persistence_duration_seconds,
            "state": self.state.value,
            "level": self.level.value,
        }
