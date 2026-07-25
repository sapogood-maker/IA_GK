"""Testes de worker.segments.segmenter.PlaySegmenter - integra GapStrategy
real + TimelineExplorer real (sintetico), sem video/YOLO/Redis."""
from __future__ import annotations

from worker.explorers.timeline_explorer import TimelineExplorer
from worker.segments.gap_strategy import GapStrategy
from worker.segments.segmenter import PlaySegmenter


def _event(
    event_type: str,
    frame_index: int,
    event_id: str,
    timestamp_seconds: float | None = None,
    track_id: int | None = None,
    entity: str | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds,
        "track_id": track_id,
        "entity": entity,
        "confidence": None,
        "position": None,
        "metadata": {},
        "parent_event_id": None,
    }


def _artifact_with_two_plays() -> dict:
    timeline = [
        _event("ObjectDetected", 0, "e1", 0.0, entity="person"),
        _event("TrackStarted", 0, "e2", 0.0, track_id=1, entity="person"),
        _event("FrameProcessed", 1, "e_fp", 0.1),  # nao decide fronteira, mas esta DENTRO do intervalo [0,2]
        _event("ObjectDetected", 2, "e3", 0.2, entity="ball"),
        _event("TrackUpdated", 2, "e4", 0.2, track_id=1, entity="person"),
        # gap grande aqui - segunda jogada
        _event("ObjectDetected", 100, "e5", 10.0, entity="person"),
        _event("TrackStarted", 100, "e6", 10.0, track_id=2, entity="person"),
        _event("FrameProcessed", 101, "e7", 10.1),  # fora do intervalo [100,100] - nao pertence a este segmento
    ]
    return {"event_timeline": timeline}


def test_segmenter_produces_two_segments_for_two_distinct_plays():
    explorer = TimelineExplorer(_artifact_with_two_plays())
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    segments = segmenter.segment(explorer)

    assert len(segments) == 2
    first, second = segments
    assert (first.start_frame, first.end_frame) == (0, 2)
    assert (second.start_frame, second.end_frame) == (100, 100)


def test_segment_events_include_non_content_events_within_range():
    """FrameProcessed (frame 1) nao decide fronteira (so eventos de
    conteudo decidem), mas PERTENCE ao primeiro segmento por estar dentro
    do intervalo [0, 2] que a GapStrategy decidiu - by_frame_range inclui
    todo tipo de evento no intervalo, nao so os de conteudo."""
    explorer = TimelineExplorer(_artifact_with_two_plays())
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    segments = segmenter.segment(explorer)
    first, second = segments

    first_ids = {e["event_id"] for e in first.events}
    assert first_ids == {"e1", "e2", "e_fp", "e3", "e4"}

    # frame 101 (FrameProcessed) fica FORA do segundo segmento ([100, 100]),
    # porque nenhum evento de conteudo o estendeu ate ali.
    second_ids = {e["event_id"] for e in second.events}
    assert second_ids == {"e5", "e6"}


def test_track_ids_and_ball_involved_are_correct_per_segment():
    explorer = TimelineExplorer(_artifact_with_two_plays())
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    segments = segmenter.segment(explorer)
    first, second = segments

    assert first.track_ids == frozenset({1})
    assert first.ball_involved is True

    assert second.track_ids == frozenset({2})
    assert second.ball_involved is False


def test_duration_and_timestamps_computed_from_segment_events():
    explorer = TimelineExplorer(_artifact_with_two_plays())
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    first = segmenter.segment(explorer)[0]

    assert first.start_timestamp == 0.0
    assert first.end_timestamp == 0.2
    assert first.duration_seconds == 0.2


def test_each_segment_has_a_unique_segment_id():
    explorer = TimelineExplorer(_artifact_with_two_plays())
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    segments = segmenter.segment(explorer)

    assert segments[0].segment_id != segments[1].segment_id


def test_empty_timeline_produces_no_segments():
    explorer = TimelineExplorer({"event_timeline": []})
    segmenter = PlaySegmenter(GapStrategy(max_gap_seconds=1.0))

    assert segmenter.segment(explorer) == []
