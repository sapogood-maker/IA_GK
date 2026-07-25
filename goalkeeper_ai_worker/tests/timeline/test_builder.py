"""Testes de worker.timeline.builder.build_timeline.

Todos constroem um ProcessorContext a mao (sem video real, sem YOLO, sem
Redis) - build_timeline e uma funcao pura do conteudo do context, e deve
ser testavel isoladamente, exatamente como o resto da Analyzer API."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from worker.analyzers.results import AnalysisResult, AnalyzerMetadata
from worker.inference.detectors.types import BoundingBox, ClassLabel, Confidence, Detection, DetectionResult
from worker.inference.events.types import MotionState, SceneAnalysisResult, SceneEvent, SceneEventType, TrackLifecycle
from worker.inference.processors.base import ProcessorContext
from worker.timeline import event_types
from worker.timeline.builder import build_timeline

FPS = 10.0


def _detection_result(frame_index: int, label: str, confidence: float = 0.9) -> DetectionResult:
    return DetectionResult(
        detections=[
            Detection(
                label=ClassLabel(label),
                confidence=Confidence(confidence),
                bbox=BoundingBox(x=10, y=20, width=30, height=40),
            )
        ],
        frame_index=frame_index,
        model_name="yolo",
        model_version="1.0.0",
        duration_ms=5.0,
    )


def test_frame_processed_events_cover_every_frame():
    context = ProcessorContext()
    timeline = build_timeline(context, fps=FPS, frame_count=3)

    frame_events = [e for e in timeline if e.event_type == event_types.FRAME_PROCESSED]
    assert [e.frame_index for e in frame_events] == [0, 1, 2]
    assert frame_events[1].timestamp_seconds == 1 / FPS


def test_object_detected_event_from_generic_label():
    context = ProcessorContext()
    context.add_detection_result(_detection_result(0, "skateboard"))

    timeline = build_timeline(context, fps=FPS, frame_count=1)

    object_events = [e for e in timeline if e.event_type == event_types.OBJECT_DETECTED]
    assert len(object_events) == 1
    event = object_events[0]
    assert event.entity == "skateboard"
    assert event.confidence == 0.9
    assert event.position == {"x": 25.0, "y": 40.0}  # centro do bbox (10+30/2, 20+40/2)
    assert event.metadata["bbox"] == {"x": 10, "y": 20, "width": 30, "height": 40}
    assert event.track_id is None  # deteccao bruta, ainda sem identidade


def test_ball_detected_event_is_emitted_alongside_object_detected():
    context = ProcessorContext()
    context.add_detection_result(_detection_result(0, "sports ball"))

    timeline = build_timeline(context, fps=FPS, frame_count=1)

    event_type_names = [e.event_type for e in timeline]
    assert event_types.OBJECT_DETECTED in event_type_names
    assert event_types.BALL_DETECTED in event_type_names
    assert event_types.PERSON_DETECTED not in event_type_names


def test_person_detected_event_is_emitted_alongside_object_detected():
    context = ProcessorContext()
    context.add_detection_result(_detection_result(0, "person"))

    timeline = build_timeline(context, fps=FPS, frame_count=1)

    event_type_names = [e.event_type for e in timeline]
    assert event_types.PERSON_DETECTED in event_type_names
    assert event_types.BALL_DETECTED not in event_type_names


def test_scene_event_is_translated_to_unified_event_type():
    context = ProcessorContext()
    scene_event = SceneEvent(
        event_type=SceneEventType.TRACK_STARTED,
        track_id=7,
        frame_index=2,
        label="person",
        motion_state=MotionState.MOVING,
        lifecycle=TrackLifecycle.NEW,
        related_track_id=None,
    )
    context.add_scene_analysis_result(
        SceneAnalysisResult(events=[scene_event], frame_index=2, analyzer_name="basic", analyzer_version="1.0.0")
    )

    timeline = build_timeline(context, fps=FPS, frame_count=3)

    scene_translated = [e for e in timeline if e.event_type == event_types.TRACK_STARTED]
    assert len(scene_translated) == 1
    event = scene_translated[0]
    assert event.track_id == 7
    assert event.entity == "person"
    assert event.frame_index == 2
    assert event.metadata["motion_state"] == "moving"
    assert event.metadata["lifecycle"] == "new"


def test_analyzer_started_and_finished_events_bracket_processing_time():
    context = ProcessorContext()
    metadata = AnalyzerMetadata(
        analyzer_name="goalkeeper_presence", analyzer_version="1.0.0", processing_time_ms=100.0
    )
    context.add_analysis_result(AnalysisResult(frame_index=5, metadata=metadata))

    timeline = build_timeline(context, fps=FPS, frame_count=6)

    started = next(e for e in timeline if e.event_type == event_types.ANALYZER_STARTED)
    finished = next(e for e in timeline if e.event_type == event_types.ANALYZER_FINISHED)

    assert finished.timestamp_seconds == 5 / FPS
    assert started.timestamp_seconds == pytest.approx(finished.timestamp_seconds - 0.1)
    assert started.metadata["analyzer_name"] == "goalkeeper_presence"


def test_base_analysis_result_without_rules_produces_no_rule_evaluated_events():
    context = ProcessorContext()
    metadata = AnalyzerMetadata(analyzer_name="goalkeeper_presence", analyzer_version="1.0.0", processing_time_ms=1.0)
    context.add_analysis_result(AnalysisResult(frame_index=0, metadata=metadata))

    timeline = build_timeline(context, fps=FPS, frame_count=1)

    rule_events = [e for e in timeline if e.event_type == event_types.RULE_EVALUATED]
    assert rule_events == []


def test_analysis_result_with_rules_produces_rule_evaluated_events_linked_to_analyzer_finished():
    @dataclass
    class _FakeRuleBasedResult(AnalysisResult):
        rules_evaluated: list
        rules_passed: list
        rules_failed: list

    metadata = AnalyzerMetadata(
        analyzer_name="goalkeeper_decision_evaluation", analyzer_version="1.0.0", processing_time_ms=2.0
    )
    result = _FakeRuleBasedResult(
        frame_index=0,
        metadata=metadata,
        rules_evaluated=["actors_visible", "decision_established"],
        rules_passed=["actors_visible"],
        rules_failed=["decision_established"],
    )
    context = ProcessorContext()
    context.add_analysis_result(result)

    timeline = build_timeline(context, fps=FPS, frame_count=1)

    rule_events = {e.metadata["rule_name"]: e for e in timeline if e.event_type == event_types.RULE_EVALUATED}
    assert set(rule_events) == {"actors_visible", "decision_established"}
    assert rule_events["actors_visible"].metadata["passed"] is True
    assert rule_events["decision_established"].metadata["passed"] is False

    finished_event = next(e for e in timeline if e.event_type == event_types.ANALYZER_FINISHED)
    assert rule_events["actors_visible"].parent_event_id == finished_event.event_id


def test_build_timeline_is_pure_and_deterministic():
    context = ProcessorContext()
    context.add_detection_result(_detection_result(0, "person"))

    first = build_timeline(context, fps=FPS, frame_count=1).to_dict()
    second = build_timeline(context, fps=FPS, frame_count=1).to_dict()

    # event_id/timestamp variam por chamada (uuid4 novo a cada Event) -
    # compara todo o resto do payload, campo a campo.
    for a, b in zip(first, second):
        assert {k: v for k, v in a.items() if k != "event_id"} == {
            k: v for k, v in b.items() if k != "event_id"
        }
