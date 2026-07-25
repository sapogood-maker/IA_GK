"""EventReference: referencia compacta a um Event (Sprint W32) - NUNCA
uma copia completa.

TemporalMemory e uma projecao RESUMIDA da Perception Timeline - nao deve
carregar fragmentos do Event Store (eventos inteiros) dentro de si,
mesmo para "o ultimo evento relevante". `TrackMemory`/`EntityMemory`
guardam um `EventReference`, nunca um `dict` de evento completo. Quem
precisar do evento inteiro consulta a Timeline original por `event_id`
(lookup por id ainda nao existe em `TimelineExplorer`, W29 - extensao
futura, fora de escopo aqui).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventReference:
    event_id: str
    event_type: str
    timestamp_seconds: float | None

    @classmethod
    def from_event(cls, event: dict) -> "EventReference":
        return cls(
            event_id=event["event_id"],
            event_type=event["event_type"],
            timestamp_seconds=event["timestamp_seconds"],
        )

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp_seconds": self.timestamp_seconds,
        }
