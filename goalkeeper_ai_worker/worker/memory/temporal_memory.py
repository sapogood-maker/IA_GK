"""TemporalMemory: container raiz da projecao agregada (Sprint W32) -
um por chamada de `build_temporal_memory`."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.memory.entity_memory import EntityMemory
from worker.memory.track_memory import TrackMemory


@dataclass(frozen=True)
class TemporalMemory:
    track_memories: dict[int, TrackMemory] = field(default_factory=dict)
    entity_memories: dict[str, EntityMemory] = field(default_factory=dict)
    frame_range: tuple[int, int] | None = None
    time_range_seconds: tuple[float, float] | None = None
    source_event_count: int = 0

    def to_dict(self) -> dict:
        return {
            "track_memories": {
                track_id: self.track_memories[track_id].to_dict() for track_id in sorted(self.track_memories)
            },
            "entity_memories": {
                entity: self.entity_memories[entity].to_dict() for entity in sorted(self.entity_memories)
            },
            "frame_range": list(self.frame_range) if self.frame_range is not None else None,
            "time_range_seconds": list(self.time_range_seconds) if self.time_range_seconds is not None else None,
            "source_event_count": self.source_event_count,
        }
