"""BasicWorldModel: primeira implementação real de `WorldModel`.

Constrói/atualiza `ObjectState` por `track_id` a partir de
`SceneAnalysisResult.objects` (o snapshot posicional que `SceneAnalyzer`
produz, Sprint W11) e do próprio histórico de `SceneEvent`s. Nenhuma
lógica de negócio - só contabilidade de estado (posição, trajetória,
cinemática, idade, visibilidade).

**Princípio de implementação:** nunca muta um `ObjectState` existente -
sempre constrói uma instância NOVA e substitui a entrada no
`WorldModelContext`. Isso garante que um `WorldState` já devolvido por
uma chamada anterior a `update()` continue sendo uma fotografia fiel
daquele instante, mesmo que o WorldModel siga avançando internamente."""
from __future__ import annotations

import time

from worker.config.settings import WorkerSettings
from worker.inference.events.types import SceneAnalysisResult, SceneEvent
from worker.inference.world.base import WorldModel
from worker.inference.world.context import WorldModelContext
from worker.inference.world.history import History
from worker.inference.world.motion import compute_motion
from worker.inference.world.object_state import ObjectState
from worker.inference.world.trajectory import Trajectory
from worker.inference.world.types import BoundingBox, ClassLabel, Confidence, ObjectId, Position
from worker.inference.world.world_state import WorldState, WorldStatistics


def _to_bbox(snapshot_bbox) -> BoundingBox:
    return BoundingBox(x=snapshot_bbox.x, y=snapshot_bbox.y, width=snapshot_bbox.width, height=snapshot_bbox.height)


def _center(bbox: BoundingBox) -> Position:
    return Position(x=bbox.x + bbox.width / 2, y=bbox.y + bbox.height / 2)


class BasicWorldModel(WorldModel):
    """Mantém `ObjectState` por `track_id`, atualizado a cada chamada a `update()`."""

    name = "basic"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._max_trajectory = settings.world_max_trajectory
        self._max_objects = settings.world_max_objects
        self._context = WorldModelContext()
        self._event_history: History[SceneEvent] = History(max_size=settings.world_history_size)

    def update(self, scene_result: SceneAnalysisResult) -> WorldState:
        start = time.monotonic()

        for event in scene_result.events:
            self._event_history.add(event)

        current_ids = {snapshot.track_id for snapshot in scene_result.objects}

        active_objects: list[ObjectState] = []
        new_objects: list[ObjectState] = []
        for snapshot in scene_result.objects:
            bbox = _to_bbox(snapshot.bbox)
            position = _center(bbox)
            existing = self._context.objects.get(snapshot.track_id)

            if existing is None:
                trajectory = Trajectory(max_length=self._max_trajectory)
                trajectory.add_point(position)
                motion = compute_motion(None, position, None)
                object_state = ObjectState(
                    track_id=ObjectId(snapshot.track_id),
                    label=ClassLabel(snapshot.label),
                    confidence=Confidence(snapshot.confidence),
                    bbox=bbox,
                    previous_bbox=None,
                    position=position,
                    motion=motion,
                    trajectory=trajectory.points,
                    age=1,
                    frames_visible=1,
                    frames_hidden=0,
                    active=True,
                    first_seen_frame=scene_result.frame_index,
                    last_seen_frame=scene_result.frame_index,
                )
                new_objects.append(object_state)
            else:
                trajectory = Trajectory(max_length=self._max_trajectory)
                for point in existing.trajectory:
                    trajectory.add_point(point)
                trajectory.add_point(position)
                motion = compute_motion(existing.position, position, existing.motion)
                object_state = ObjectState(
                    track_id=existing.track_id,
                    label=ClassLabel(snapshot.label),
                    confidence=Confidence(snapshot.confidence),
                    bbox=bbox,
                    previous_bbox=existing.bbox,
                    position=position,
                    motion=motion,
                    trajectory=trajectory.points,
                    age=existing.age + 1,
                    frames_visible=existing.frames_visible + 1,
                    frames_hidden=0,
                    active=True,
                    first_seen_frame=existing.first_seen_frame,
                    last_seen_frame=scene_result.frame_index,
                )

            self._context.objects[snapshot.track_id] = object_state
            active_objects.append(object_state)

        lost_objects: list[ObjectState] = []
        for track_id, object_state in list(self._context.objects.items()):
            if track_id in current_ids:
                continue
            updated = ObjectState(
                track_id=object_state.track_id,
                label=object_state.label,
                confidence=object_state.confidence,
                bbox=object_state.bbox,
                previous_bbox=object_state.previous_bbox,
                position=object_state.position,
                motion=object_state.motion,
                trajectory=object_state.trajectory,
                age=object_state.age,
                frames_visible=object_state.frames_visible,
                frames_hidden=object_state.frames_hidden + 1,
                active=False,
                first_seen_frame=object_state.first_seen_frame,
                last_seen_frame=object_state.last_seen_frame,
            )
            self._context.objects[track_id] = updated
            lost_objects.append(updated)

        self._evict_if_over_capacity()
        lost_objects = [obj for obj in lost_objects if obj.track_id in self._context.objects]

        duration_ms = (time.monotonic() - start) * 1000
        average_speed = (
            sum(obj.motion.speed for obj in active_objects) / len(active_objects) if active_objects else 0.0
        )
        statistics = WorldStatistics(
            object_count=len(self._context.objects),
            active_tracks=len(active_objects),
            lost_tracks=len(lost_objects),
            new_tracks=len(new_objects),
            average_speed=average_speed,
        )
        return WorldState(
            frame_index=scene_result.frame_index,
            active_objects=active_objects,
            lost_objects=lost_objects,
            new_objects=new_objects,
            recent_events=self._event_history.to_list(),
            statistics=statistics,
        )

    def _evict_if_over_capacity(self) -> None:
        """Remove os objetos LOST mais antigos (por `last_seen_frame`)
        quando o total excede `WORKER_WORLD_MAX_OBJECTS` - nunca remove
        um objeto ativo. `max_objects <= 0` desativa o limite."""
        if self._max_objects <= 0 or len(self._context.objects) <= self._max_objects:
            return

        lost_track_ids = sorted(
            (track_id for track_id, obj in self._context.objects.items() if not obj.active),
            key=lambda track_id: self._context.objects[track_id].last_seen_frame,
        )
        excess = len(self._context.objects) - self._max_objects
        for track_id in lost_track_ids[:excess]:
            del self._context.objects[track_id]

    def reset(self) -> None:
        self._context.reset()
        self._event_history.reset()
