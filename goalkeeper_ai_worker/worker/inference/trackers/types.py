"""Tipos próprios da API de Tracking - nunca listas de dicionários soltos.

Deliberadamente independentes dos tipos de `worker.inference.detectors`
(mesmo padrão x/y/width/height, `ClassLabel`/`Confidence` como NewType) -
`trackers/` nunca importa de `detectors/` além do contrato de entrada
(`DetectionResult`, em `base.py`), preservando as duas famílias
desacopladas entre si (a pequena duplicação de tipos é deliberada, ver
AI_WORKER_CONSTITUTION.md, Seção 6.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NewType

TrackId = NewType("TrackId", int)
ClassLabel = NewType("ClassLabel", str)
Confidence = NewType("Confidence", float)


@dataclass(frozen=True)
class BoundingBox:
    """Caixa delimitadora de um objeto rastreado, em pixels."""

    x: int
    y: int
    width: int
    height: int


class TrackState(str, Enum):
    """Estado de uma trilha no momento em que este TrackedObject foi produzido."""

    NEW = "new"
    TRACKED = "tracked"
    LOST = "lost"
    REMOVED = "removed"


@dataclass(frozen=True)
class TrackedObject:
    """Um objeto com identidade persistente entre frames."""

    track_id: TrackId
    label: ClassLabel
    confidence: Confidence
    bbox: BoundingBox
    age: int
    state: TrackState
    frame_index: int


@dataclass
class TrackingStatistics:
    """Estatísticas agregadas do Tracker no momento de uma chamada a `track()`."""

    total_tracks: int = 0
    active_tracks: int = 0
    lost_tracks: int = 0
    removed_tracks: int = 0

    def to_dict(self) -> dict:
        return {
            "total_tracks": self.total_tracks,
            "active_tracks": self.active_tracks,
            "lost_tracks": self.lost_tracks,
            "removed_tracks": self.removed_tracks,
        }


@dataclass
class TrackingResult:
    """Resultado completo de uma chamada a `Tracker.track(detections)`."""

    tracked_objects: list[TrackedObject] = field(default_factory=list)
    frame_index: int = 0
    tracker_name: str = ""
    tracker_version: str = ""
    duration_ms: float = 0.0
    statistics: TrackingStatistics = field(default_factory=TrackingStatistics)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "tracker_name": self.tracker_name,
            "tracker_version": self.tracker_version,
            "duration_ms": self.duration_ms,
            "statistics": self.statistics.to_dict(),
            "tracked_objects": [
                {
                    "track_id": obj.track_id,
                    "label": obj.label,
                    "confidence": obj.confidence,
                    "bbox": {
                        "x": obj.bbox.x,
                        "y": obj.bbox.y,
                        "width": obj.bbox.width,
                        "height": obj.bbox.height,
                    },
                    "age": obj.age,
                    "state": obj.state.value,
                    "frame_index": obj.frame_index,
                }
                for obj in self.tracked_objects
            ],
        }
