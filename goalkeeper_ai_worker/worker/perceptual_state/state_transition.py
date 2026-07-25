"""StateTransition: registro compacto de "a última mudança" (Sprint W33).

Nunca inventa um estado anterior sem dado - `None` quando não há
histórico suficiente para saber o que veio antes."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateTransition:
    dimension: str  # "motion" | "presence"
    from_state: str
    to_state: str
    frame_index: int | None
    timestamp_seconds: float | None

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "frame_index": self.frame_index,
            "timestamp_seconds": self.timestamp_seconds,
        }
