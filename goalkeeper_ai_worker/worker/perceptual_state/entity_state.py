"""EntityState: agregação factual do estado atual de todos os track_id
sob o mesmo rótulo normalizado (Sprint W33) - ex. "ball".

`motion_state_counts` e uma contagem factual (ex. {"moving": 2,
"stopped": 1}) - NUNCA um "estado dominante" (isso seria interpretacao,
fora de escopo)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityState:
    entity: str
    active_track_ids: frozenset[int] = frozenset()
    ended_track_ids: frozenset[int] = frozenset()
    motion_state_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "active_track_ids": sorted(self.active_track_ids),
            "ended_track_ids": sorted(self.ended_track_ids),
            "motion_state_counts": dict(sorted(self.motion_state_counts.items())),
        }
