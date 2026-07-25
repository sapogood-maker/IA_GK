"""Testes de worker.segments.gap_strategy.GapStrategy."""
from __future__ import annotations

from worker.segments.gap_strategy import GapStrategy


def _event(event_type: str, frame_index: int, timestamp_seconds: float | None) -> dict:
    return {"event_type": event_type, "frame_index": frame_index, "timestamp_seconds": timestamp_seconds}


def test_empty_timeline_produces_no_boundaries():
    strategy = GapStrategy(max_gap_seconds=1.0)
    assert strategy.find_boundaries([]) == []


def test_timeline_with_no_content_events_produces_no_boundaries():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [_event("FrameProcessed", i, i * 0.1) for i in range(5)]
    assert strategy.find_boundaries(events) == []


def test_all_content_events_within_gap_form_a_single_segment():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [
        _event("ObjectDetected", 0, 0.0),
        _event("TrackStarted", 0, 0.0),
        _event("TrackUpdated", 5, 0.5),
        _event("TrackUpdated", 10, 1.0),
    ]
    assert strategy.find_boundaries(events) == [(0, 10)]


def test_gap_larger_than_threshold_splits_into_two_segments():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [
        _event("ObjectDetected", 0, 0.0),
        _event("TrackUpdated", 5, 0.5),
        # gap de 3.0s > 1.0s aqui
        _event("ObjectDetected", 100, 3.5),
        _event("TrackUpdated", 105, 4.0),
    ]
    assert strategy.find_boundaries(events) == [(0, 5), (100, 105)]


def test_frame_processed_alone_never_counts_as_content():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [
        _event("ObjectDetected", 0, 0.0),
        _event("FrameProcessed", 1, 0.1),
        _event("FrameProcessed", 2, 0.2),
        # Sem esse ObjectDetected, o gap de FrameProcessed sozinho nao conta -
        # so existem 2 eventos de conteudo, ambos dentro do gap.
        _event("ObjectDetected", 3, 0.3),
    ]
    assert strategy.find_boundaries(events) == [(0, 3)]


def test_events_without_timestamp_never_split_a_segment():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [
        _event("ObjectDetected", 0, None),
        _event("TrackUpdated", 100, None),
    ]
    assert strategy.find_boundaries(events) == [(0, 100)]


def test_single_content_event_produces_single_frame_segment():
    strategy = GapStrategy(max_gap_seconds=1.0)
    events = [_event("ObjectDetected", 42, 4.2)]
    assert strategy.find_boundaries(events) == [(42, 42)]


def test_custom_content_event_types_are_honored():
    strategy = GapStrategy(max_gap_seconds=1.0, content_event_types=frozenset({"BallDetected"}))
    events = [
        _event("ObjectDetected", 0, 0.0),  # ignorado - nao esta no set customizado
        _event("BallDetected", 5, 0.5),
    ]
    assert strategy.find_boundaries(events) == [(5, 5)]
