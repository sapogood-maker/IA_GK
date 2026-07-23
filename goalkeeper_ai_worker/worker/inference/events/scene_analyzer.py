"""BasicSceneAnalyzer: primeira implementação real de `SceneAnalyzer`.

Deriva eventos genéricos de cena comparando o `TrackingResult` do frame
atual contra a memória interna (`SceneAnalysisContext`) das trilhas já
observadas. Nenhuma lógica específica de futebol - só transições de
ciclo de vida de trilha, movimento e oclusão geométrica.

**Nota de design, documentada honestamente:** com `analyze()` recebendo
apenas um `TrackingResult` (sem dimensões do frame), `OBJECT_ENTERED_FRAME`/
`OBJECT_LEFT_FRAME` são emitidos no MESMO momento que `TRACK_STARTED`/
`TRACK_LOST` respectivamente - a única informação disponível sobre
"visibilidade" de um objeto é a própria presença/ausência no
TrackingResult, não a posição geométrica em relação às bordas do frame."""
from __future__ import annotations

import time

from worker.config.settings import WorkerSettings
from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.context import SceneAnalysisContext, TrackObservation
from worker.inference.events.types import (
    MotionState,
    SceneAnalysisResult,
    SceneEvent,
    SceneEventType,
    SceneObjectSnapshot,
    SceneStatistics,
    TrackLifecycle,
)
from worker.inference.trackers.types import BoundingBox, TrackedObject, TrackingResult


def _center(bbox: BoundingBox) -> tuple[float, float]:
    return (bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _iou(a: BoundingBox, b: BoundingBox) -> float:
    ax1, ay1, ax2, ay2 = a.x, a.y, a.x + a.width, a.y + a.height
    bx1, by1, bx2, by2 = b.x, b.y, b.x + b.width, b.y + b.height

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_width, inter_height = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    intersection = inter_width * inter_height
    if intersection <= 0.0:
        return 0.0

    area_a = a.width * a.height
    area_b = b.width * b.height
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


class BasicSceneAnalyzer(SceneAnalyzer):
    """Deriva eventos genéricos de cena a partir de TrackingResults sucessivos."""

    name = "basic"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._motion_threshold_px = settings.scene_motion_threshold_px
        self._occlusion_iou_threshold = settings.scene_occlusion_iou_threshold
        self._context = SceneAnalysisContext()
        self._cumulative_total_events = 0
        self._cumulative_events_by_type: dict[str, int] = {}

    def analyze(self, tracking_result: TrackingResult) -> SceneAnalysisResult:
        start = time.monotonic()
        events: list[SceneEvent] = []
        current_ids = {obj.track_id for obj in tracking_result.tracked_objects}

        for obj in tracking_result.tracked_objects:
            events.extend(self._observe(obj))

        events.extend(self._detect_lost_tracks(current_ids, tracking_result.frame_index))
        events.extend(self._detect_occlusions(tracking_result))

        duration_ms = (time.monotonic() - start) * 1000
        statistics = self._compute_statistics(events)
        objects = [
            SceneObjectSnapshot(
                track_id=obj.track_id, label=obj.label, confidence=obj.confidence, bbox=obj.bbox
            )
            for obj in tracking_result.tracked_objects
        ]

        return SceneAnalysisResult(
            events=events,
            objects=objects,
            frame_index=tracking_result.frame_index,
            analyzer_name=self.name,
            analyzer_version=self.version,
            duration_ms=duration_ms,
            statistics=statistics,
        )

    def _observe(self, obj: TrackedObject) -> list[SceneEvent]:
        events: list[SceneEvent] = []
        observation = self._context.observations.get(obj.track_id)

        if observation is None:
            events.append(
                SceneEvent(
                    event_type=SceneEventType.TRACK_STARTED,
                    track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                    lifecycle=TrackLifecycle.NEW,
                )
            )
            events.append(
                SceneEvent(
                    event_type=SceneEventType.OBJECT_ENTERED_FRAME,
                    track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                )
            )
            motion_state = MotionState.UNKNOWN
        elif observation.lifecycle == TrackLifecycle.LOST:
            events.append(
                SceneEvent(
                    event_type=SceneEventType.TRACK_RECOVERED,
                    track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                    lifecycle=TrackLifecycle.ACTIVE,
                )
            )
            motion_state = MotionState.UNKNOWN
        else:
            displacement = _distance(_center(observation.bbox), _center(obj.bbox))
            new_motion = (
                MotionState.STOPPED if displacement < self._motion_threshold_px else MotionState.MOVING
            )
            if observation.motion_state == MotionState.MOVING and new_motion == MotionState.STOPPED:
                events.append(
                    SceneEvent(
                        event_type=SceneEventType.OBJECT_STOPPED,
                        track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                        motion_state=new_motion,
                    )
                )
            elif observation.motion_state == MotionState.STOPPED and new_motion == MotionState.MOVING:
                events.append(
                    SceneEvent(
                        event_type=SceneEventType.OBJECT_MOVING,
                        track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                        motion_state=new_motion,
                    )
                )
            else:
                events.append(
                    SceneEvent(
                        event_type=SceneEventType.TRACK_UPDATED,
                        track_id=obj.track_id, frame_index=obj.frame_index, label=obj.label,
                        motion_state=new_motion,
                    )
                )
            motion_state = new_motion

        self._context.observations[obj.track_id] = TrackObservation(
            track_id=obj.track_id, label=obj.label, bbox=obj.bbox,
            last_seen_frame=obj.frame_index, lifecycle=TrackLifecycle.ACTIVE, motion_state=motion_state,
        )
        return events

    def _detect_lost_tracks(self, current_ids: set[int], frame_index: int) -> list[SceneEvent]:
        events: list[SceneEvent] = []
        for track_id, observation in self._context.observations.items():
            if track_id not in current_ids and observation.lifecycle == TrackLifecycle.ACTIVE:
                events.append(
                    SceneEvent(
                        event_type=SceneEventType.TRACK_LOST,
                        track_id=track_id, frame_index=frame_index, label=observation.label,
                        lifecycle=TrackLifecycle.LOST,
                    )
                )
                events.append(
                    SceneEvent(
                        event_type=SceneEventType.OBJECT_LEFT_FRAME,
                        track_id=track_id, frame_index=frame_index, label=observation.label,
                    )
                )
                observation.lifecycle = TrackLifecycle.LOST
        return events

    def _detect_occlusions(self, tracking_result: TrackingResult) -> list[SceneEvent]:
        events: list[SceneEvent] = []
        objects = tracking_result.tracked_objects
        for i, first in enumerate(objects):
            for second in objects[i + 1 :]:
                if _iou(first.bbox, second.bbox) >= self._occlusion_iou_threshold:
                    events.append(
                        SceneEvent(
                            event_type=SceneEventType.OCCLUSION_DETECTED,
                            track_id=first.track_id, frame_index=tracking_result.frame_index,
                            label=first.label, related_track_id=second.track_id,
                        )
                    )
        return events

    def _compute_statistics(self, new_events: list[SceneEvent]) -> SceneStatistics:
        """Estatísticas CUMULATIVAS (todo o histórico já observado por esta
        instância, não só os eventos deste frame) - mesmo padrão de
        `TrackingStatistics` (Seção 6.1, W9), que também reflete o estado
        acumulado do Tracker, não só a chamada mais recente."""
        for event in new_events:
            self._cumulative_events_by_type[event.event_type.value] = (
                self._cumulative_events_by_type.get(event.event_type.value, 0) + 1
            )
        self._cumulative_total_events += len(new_events)

        active_tracks = sum(
            1 for observation in self._context.observations.values()
            if observation.lifecycle == TrackLifecycle.ACTIVE
        )
        lost_tracks = sum(
            1 for observation in self._context.observations.values()
            if observation.lifecycle == TrackLifecycle.LOST
        )
        return SceneStatistics(
            total_tracks_observed=len(self._context.observations),
            active_tracks=active_tracks,
            lost_tracks=lost_tracks,
            total_events=self._cumulative_total_events,
            events_by_type=dict(self._cumulative_events_by_type),
        )

    def reset(self) -> None:
        self._context.reset()
        self._cumulative_total_events = 0
        self._cumulative_events_by_type = {}
