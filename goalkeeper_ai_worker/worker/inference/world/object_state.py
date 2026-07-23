"""ObjectState: estado próprio de um único objeto do mundo - nenhuma
lógica específica de goleiro/futebol.

Cada `update()` do `WorldModel` (`world_model.py`) constrói uma instância
NOVA (nunca muta uma existente) - garante que um `WorldState` já
devolvido continue sendo uma fotografia fiel daquele instante, mesmo que
o `WorldModel` continue avançando internamente."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.inference.world.types import BoundingBox, ClassLabel, Confidence, Motion, ObjectId, Position


@dataclass
class ObjectState:
    """Estado completo de um objeto do mundo num dado frame."""

    track_id: ObjectId
    label: ClassLabel
    confidence: Confidence
    bbox: BoundingBox
    previous_bbox: BoundingBox | None
    position: Position
    motion: Motion
    trajectory: list[Position] = field(default_factory=list)
    age: int = 0
    frames_visible: int = 0
    frames_hidden: int = 0
    active: bool = True
    first_seen_frame: int = 0
    last_seen_frame: int = 0

    @property
    def time_in_scene_frames(self) -> int:
        """"Tempo em cena", em número de frames - o World Model não
        recebe fps (só frame_index), então não há como expressar isso em
        segundos sem um dado adicional que hoje não existe nesta camada."""
        return self.last_seen_frame - self.first_seen_frame + 1

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence": self.confidence,
            "bbox": {"x": self.bbox.x, "y": self.bbox.y, "width": self.bbox.width, "height": self.bbox.height},
            "previous_bbox": (
                {
                    "x": self.previous_bbox.x, "y": self.previous_bbox.y,
                    "width": self.previous_bbox.width, "height": self.previous_bbox.height,
                }
                if self.previous_bbox is not None
                else None
            ),
            "position": {"x": self.position.x, "y": self.position.y},
            "motion": self.motion.to_dict(),
            "trajectory": [{"x": point.x, "y": point.y} for point in self.trajectory],
            "age": self.age,
            "frames_visible": self.frames_visible,
            "frames_hidden": self.frames_hidden,
            "active": self.active,
            "first_seen_frame": self.first_seen_frame,
            "last_seen_frame": self.last_seen_frame,
            "time_in_scene_frames": self.time_in_scene_frames,
        }
