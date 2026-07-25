"""Evidence: um fato literal de WorkingState citado como base de uma
hipótese (Sprint W34) - nunca um fato de Timeline/Event."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    field: str  # ex.: "motion_state" - sempre um campo de TrackState/EntityState
    value: str  # ex.: "stopped"

    def to_dict(self) -> dict:
        return {"field": self.field, "value": self.value}
