"""PlaySegmenter: monta PlaySegments a partir de uma SegmentStrategy +
um TimelineExplorer (Sprint W30).

Nunca decide ONDE cortar (isso e responsabilidade exclusiva da
SegmentStrategy injetada) - so monta o PlaySegment para cada intervalo
que a estrategia devolveu, reaproveitando TimelineExplorer.chronological()
e TimelineExplorer.by_frame_range() (Sprint W29) em vez de reimplementar
filtragem de eventos por frame."""
from __future__ import annotations

from uuid import uuid4

from worker.explorers.timeline_explorer import TimelineExplorer
from worker.segments.play_segment import PlaySegment
from worker.segments.strategy import SegmentStrategy


class PlaySegmenter:
    def __init__(self, strategy: SegmentStrategy) -> None:
        self._strategy = strategy

    def segment(self, explorer: TimelineExplorer) -> list[PlaySegment]:
        events = explorer.chronological()
        boundaries = self._strategy.find_boundaries(events)

        segments = []
        for start_frame, end_frame in boundaries:
            segment_events = explorer.by_frame_range(start_frame, end_frame)
            segments.append(self._build_segment(start_frame, end_frame, segment_events))
        return segments

    @staticmethod
    def _build_segment(start_frame: int, end_frame: int, events: list[dict]) -> PlaySegment:
        track_ids = frozenset(e["track_id"] for e in events if e["track_id"] is not None)
        ball_involved = any(e["entity"] == "ball" for e in events)

        timestamps = [e["timestamp_seconds"] for e in events if e["timestamp_seconds"] is not None]
        start_timestamp = min(timestamps) if timestamps else None
        end_timestamp = max(timestamps) if timestamps else None
        duration_seconds = (
            end_timestamp - start_timestamp if start_timestamp is not None and end_timestamp is not None else None
        )

        return PlaySegment(
            segment_id=str(uuid4()),
            start_frame=start_frame,
            end_frame=end_frame,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            duration_seconds=duration_seconds,
            track_ids=track_ids,
            ball_involved=ball_involved,
            events=events,
        )
