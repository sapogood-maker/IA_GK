"""Tipos próprios da API de Eventos de Cena - nunca listas de dicionários
soltos.

Nenhum tipo aqui é específico de futebol - `SceneEventType` cobre só
transições genéricas de trilha/movimento/oclusão. Análises específicas
futuras (defesa, gol, chute) consomem `SceneEvent`, nunca o alteram."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SceneEventType(str, Enum):
    """Todo tipo de evento de cena reconhecido nesta sprint - genérico,
    sem nenhuma semântica de futebol."""

    TRACK_STARTED = "track_started"
    TRACK_UPDATED = "track_updated"
    TRACK_LOST = "track_lost"
    TRACK_RECOVERED = "track_recovered"
    OBJECT_ENTERED_FRAME = "object_entered_frame"
    OBJECT_LEFT_FRAME = "object_left_frame"
    OBJECT_STOPPED = "object_stopped"
    OBJECT_MOVING = "object_moving"
    OCCLUSION_DETECTED = "occlusion_detected"


class MotionState(str, Enum):
    """Estado de movimento observado de uma trilha entre dois frames."""

    UNKNOWN = "unknown"
    MOVING = "moving"
    STOPPED = "stopped"


class TrackLifecycle(str, Enum):
    """Estado de ciclo de vida de uma trilha, do ponto de vista do
    SceneAnalyzer (memória própria em `context.py` - independente do
    ciclo de vida interno do Tracker)."""

    NEW = "new"
    ACTIVE = "active"
    LOST = "lost"


@dataclass(frozen=True)
class SceneEvent:
    """Um evento de interpretação de cena - sempre associado a uma
    trilha (`track_id`) e a um frame."""

    event_type: SceneEventType
    track_id: int
    frame_index: int
    label: str = ""
    motion_state: MotionState | None = None
    lifecycle: TrackLifecycle | None = None
    related_track_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "track_id": self.track_id,
            "frame_index": self.frame_index,
            "label": self.label,
            "motion_state": self.motion_state.value if self.motion_state is not None else None,
            "lifecycle": self.lifecycle.value if self.lifecycle is not None else None,
            "related_track_id": self.related_track_id,
        }


@dataclass
class SceneStatistics:
    """Estatísticas agregadas do SceneAnalyzer no momento de uma chamada
    a `analyze()` - cumulativas, refletem todo o histórico já observado."""

    total_tracks_observed: int = 0
    active_tracks: int = 0
    lost_tracks: int = 0
    total_events: int = 0
    events_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_tracks_observed": self.total_tracks_observed,
            "active_tracks": self.active_tracks,
            "lost_tracks": self.lost_tracks,
            "total_events": self.total_events,
            "events_by_type": dict(self.events_by_type),
        }


@dataclass
class SceneAnalysisResult:
    """Resultado completo de uma chamada a `SceneAnalyzer.analyze(tracking_result)`."""

    events: list[SceneEvent] = field(default_factory=list)
    frame_index: int = 0
    analyzer_name: str = ""
    analyzer_version: str = ""
    duration_ms: float = 0.0
    statistics: SceneStatistics = field(default_factory=SceneStatistics)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "analyzer_name": self.analyzer_name,
            "analyzer_version": self.analyzer_version,
            "duration_ms": self.duration_ms,
            "statistics": self.statistics.to_dict(),
            "events": [event.to_dict() for event in self.events],
        }
