"""PlaySegment: estrutura de dados de um segmento de jogada (Sprint W30).

Puramente estrutural - nenhum campo de texto pronto/resumo. Geracao de
texto humano e responsabilidade do CLI (worker/explorers/cli.py), nunca
desta classe nem do TimelineExplorer (evita acoplar W29 a W30 - a
direcao de dependencia certa e Segmenter -> Explorer, nunca o contrario).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaySegment:
    """Um intervalo de frames da Perception Timeline, com os eventos que
    pertencem a ele e um resumo estrutural de quem participou."""

    segment_id: str
    start_frame: int
    end_frame: int
    start_timestamp: float | None
    end_timestamp: float | None
    duration_seconds: float | None
    track_ids: frozenset[int]
    ball_involved: bool
    events: list[dict]

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "duration_seconds": self.duration_seconds,
            "track_ids": sorted(self.track_ids),
            "ball_involved": self.ball_involved,
            "event_count": len(self.events),
            "events": self.events,
        }
