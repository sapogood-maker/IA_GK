"""ConvictionSet: raiz do conjunto de convicções (Sprint W35) - um por
chamada de `update_convictions`.

Diferente de `HypothesisSet` (tuplas, pois um track pode gerar várias
hipóteses), `ConvictionSet` usa DICTS chaveados por `hypothesis_id` -
aqui a granularidade já é "uma Conviction por hipótese distinta", então
a chave natural é única por construção, igual a
`WorkingState.track_states`."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.conviction.entity_conviction import EntityConviction
from worker.conviction.track_conviction import TrackConviction


@dataclass(frozen=True)
class ConvictionSet:
    track_convictions: dict[str, TrackConviction] = field(default_factory=dict)
    entity_convictions: dict[str, EntityConviction] = field(default_factory=dict)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None

    def to_dict(self) -> dict:
        return {
            "track_convictions": {
                hid: self.track_convictions[hid].to_dict() for hid in sorted(self.track_convictions)
            },
            "entity_convictions": {
                hid: self.entity_convictions[hid].to_dict() for hid in sorted(self.entity_convictions)
            },
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
        }
