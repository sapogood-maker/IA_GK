"""WorldState: a fotografia completa da cena num dado frame.

`WorldState` é o único tipo que os futuros analisadores específicos de
futebol (`GoalkeeperAnalyzer`, `BallAnalyzer`, `SaveAnalyzer`,
`ShotAnalyzer`, `DiveAnalyzer`, `GoalAnalyzer`, Sprint W12+) poderão
consumir - nenhum deles conhecerá `Detector`/`Tracker`/`SceneAnalyzer`."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.inference.events.types import SceneEvent
from worker.inference.world.object_state import ObjectState


@dataclass
class WorldStatistics:
    """Estatísticas agregadas do World Model no momento de uma chamada a
    `update()` - refletem o estado atual (não cumulativas de eventos, ao
    contrário de `SceneStatistics`/`TrackingStatistics` - aqui faz mais
    sentido reportar a contagem "agora", já que WorldState é uma
    fotografia, não um log)."""

    object_count: int = 0
    active_tracks: int = 0
    lost_tracks: int = 0
    new_tracks: int = 0
    average_speed: float = 0.0

    def to_dict(self) -> dict:
        return {
            "object_count": self.object_count,
            "active_tracks": self.active_tracks,
            "lost_tracks": self.lost_tracks,
            "new_tracks": self.new_tracks,
            "average_speed": self.average_speed,
        }


@dataclass
class WorldState:
    """Fotografia completa do mundo observado num dado frame."""

    frame_index: int = 0
    active_objects: list[ObjectState] = field(default_factory=list)
    lost_objects: list[ObjectState] = field(default_factory=list)
    new_objects: list[ObjectState] = field(default_factory=list)
    recent_events: list[SceneEvent] = field(default_factory=list)
    statistics: WorldStatistics = field(default_factory=WorldStatistics)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "active_objects": [obj.to_dict() for obj in self.active_objects],
            "lost_objects": [obj.to_dict() for obj in self.lost_objects],
            "new_objects": [obj.to_dict() for obj in self.new_objects],
            "recent_events": [event.to_dict() for event in self.recent_events],
            "statistics": self.statistics.to_dict(),
        }
