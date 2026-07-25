"""build_timeline: traduz um `ProcessorContext` ja preenchido numa
`PerceptionTimeline` (Sprint W28).

Roda UMA UNICA VEZ, depois que o loop de frames de `BasicVisionEngine`
termina - nao dentro dele. Isso e proposital: todo dado de que este
modulo precisa (`context.detections`, `context.scene_analysis_results`,
`context.analysis_results`) ja e acumulado, frame a frame, pelo proprio
`ProcessorContext` (worker/inference/processors/base.py) - nenhum
Detector/Tracker/SceneAnalyzer/WorldModel/FootballDomain/Analyzer precisa
mudar para a Timeline existir. Este modulo so LE o que ja foi produzido e
traduz para o schema unificado de `Event`.

Funcao pura: dado o mesmo `ProcessorContext`/`fps`/`frame_count`, sempre
produz a mesma `PerceptionTimeline` - testavel sem video real, sem YOLO,
sem Redis (ver tests/timeline/test_builder.py).
"""
from __future__ import annotations

from worker.inference.processors.base import ProcessorContext
from worker.timeline import event_types
from worker.timeline.event import Event
from worker.timeline.timeline import PerceptionTimeline

_BALL_LABELS = {"sports ball"}
_PERSON_LABELS = {"person"}


def build_timeline(context: ProcessorContext, fps: float, frame_count: int) -> PerceptionTimeline:
    timeline = PerceptionTimeline()
    timeline.extend(_frame_processed_events(frame_count, fps))
    timeline.extend(_detection_events(context, fps))
    timeline.extend(_scene_events(context, fps))
    timeline.extend(_analyzer_events(context, fps))
    return timeline


def _timestamp(frame_index: int, fps: float) -> float | None:
    return (frame_index / fps) if fps else None


def _bbox_center(bbox) -> dict:
    return {"x": bbox.x + bbox.width / 2, "y": bbox.y + bbox.height / 2}


def _frame_processed_events(frame_count: int, fps: float):
    for frame_index in range(frame_count):
        yield Event(
            event_type=event_types.FRAME_PROCESSED,
            frame_index=frame_index,
            timestamp_seconds=_timestamp(frame_index, fps),
            track_id=None,
            entity=None,
            position=None,
            confidence=None,
            metadata={},
        )


def _detection_events(context: ProcessorContext, fps: float):
    for detection_result in context.detections:
        for detection in detection_result.detections:
            common = dict(
                frame_index=detection_result.frame_index,
                timestamp_seconds=_timestamp(detection_result.frame_index, fps),
                track_id=None,
                position=_bbox_center(detection.bbox),
                confidence=float(detection.confidence),
                metadata={
                    "label": detection.label,
                    "bbox": {
                        "x": detection.bbox.x,
                        "y": detection.bbox.y,
                        "width": detection.bbox.width,
                        "height": detection.bbox.height,
                    },
                    "model_name": detection_result.model_name,
                },
            )
            yield Event(event_type=event_types.OBJECT_DETECTED, entity=detection.label, **common)
            if detection.label in _BALL_LABELS:
                yield Event(event_type=event_types.BALL_DETECTED, entity="ball", **common)
            elif detection.label in _PERSON_LABELS:
                yield Event(event_type=event_types.PERSON_DETECTED, entity="person", **common)


def _scene_events(context: ProcessorContext, fps: float):
    for scene_result in context.scene_analysis_results:
        for scene_event in scene_result.events:
            event_type = event_types.FROM_SCENE_EVENT_TYPE.get(
                scene_event.event_type.value, scene_event.event_type.value
            )
            yield Event(
                event_type=event_type,
                frame_index=scene_event.frame_index,
                timestamp_seconds=_timestamp(scene_event.frame_index, fps),
                track_id=scene_event.track_id,
                entity=scene_event.label or None,
                position=None,
                confidence=None,
                metadata={
                    "motion_state": scene_event.motion_state.value if scene_event.motion_state else None,
                    "lifecycle": scene_event.lifecycle.value if scene_event.lifecycle else None,
                    "related_track_id": scene_event.related_track_id,
                },
            )


def _analyzer_events(context: ProcessorContext, fps: float):
    for result in context.analysis_results:
        analyzer_name = result.metadata.analyzer_name
        analyzer_version = result.metadata.analyzer_version
        processing_time_ms = result.metadata.processing_time_ms
        finished_ts = _timestamp(result.frame_index, fps)
        started_ts = (
            finished_ts - (processing_time_ms / 1000.0) if finished_ts is not None else None
        )

        yield Event(
            event_type=event_types.ANALYZER_STARTED,
            frame_index=result.frame_index,
            timestamp_seconds=started_ts,
            track_id=None,
            entity=None,
            position=None,
            confidence=None,
            metadata={"analyzer_name": analyzer_name, "analyzer_version": analyzer_version},
        )
        finished_event = Event(
            event_type=event_types.ANALYZER_FINISHED,
            frame_index=result.frame_index,
            timestamp_seconds=finished_ts,
            track_id=None,
            entity=None,
            position=None,
            confidence=None,
            metadata={
                "analyzer_name": analyzer_name,
                "analyzer_version": analyzer_version,
                "processing_time_ms": processing_time_ms,
            },
        )
        yield finished_event

        # Duck-typing deliberado: so os Analyzers de Rule Evaluation (W23+)
        # tem estes atributos - AnalysisResult base nao. Um resultado sem
        # eles simplesmente nao produz nenhum RuleEvaluated, sem erro.
        rules_evaluated = getattr(result, "rules_evaluated", None)
        if rules_evaluated:
            rules_passed = set(getattr(result, "rules_passed", []) or [])
            rules_failed = set(getattr(result, "rules_failed", []) or [])
            for rule_name in rules_evaluated:
                yield Event(
                    event_type=event_types.RULE_EVALUATED,
                    frame_index=result.frame_index,
                    timestamp_seconds=finished_ts,
                    track_id=None,
                    entity=None,
                    position=None,
                    confidence=None,
                    metadata={
                        "analyzer_name": analyzer_name,
                        "rule_name": rule_name,
                        "passed": rule_name in rules_passed,
                        "failed": rule_name in rules_failed,
                    },
                    parent_event_id=finished_event.event_id,
                )
