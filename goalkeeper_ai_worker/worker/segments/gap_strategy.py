"""GapStrategy: unica SegmentStrategy implementada na Sprint W30.

Fecha um segmento quando o intervalo de tempo entre dois eventos de
"conteudo" consecutivos excede `max_gap_seconds` - mesma tecnica de
segmentacao por silencio ja padrao em analise de audio/video, nao um
modelo/heuristica de dominio de futebol.

So ObjectDetected/TrackStarted/TrackUpdated/TrackRecovered contam como
"conteudo" - FrameProcessed sozinho nunca abre nem fecha segmento (existe
em todo frame, inclusive vazios; usa-lo aqui colapsaria tudo num unico
segmento gigante)."""
from __future__ import annotations

from worker.segments.strategy import SegmentStrategy
from worker.timeline import event_types

_DEFAULT_CONTENT_EVENT_TYPES = frozenset(
    {
        event_types.OBJECT_DETECTED,
        event_types.TRACK_STARTED,
        event_types.TRACK_UPDATED,
        event_types.TRACK_RECOVERED,
    }
)


class GapStrategy(SegmentStrategy):
    name = "gap"

    def __init__(
        self,
        max_gap_seconds: float = 1.0,
        content_event_types: frozenset[str] | None = None,
    ) -> None:
        self._max_gap_seconds = max_gap_seconds
        self._content_event_types = content_event_types or _DEFAULT_CONTENT_EVENT_TYPES

    def find_boundaries(self, events: list[dict]) -> list[tuple[int, int]]:
        content_events = [e for e in events if e["event_type"] in self._content_event_types]
        if not content_events:
            return []

        boundaries: list[tuple[int, int]] = []
        segment_start = content_events[0]["frame_index"]
        previous = content_events[0]

        for event in content_events[1:]:
            gap = self._time_gap(previous, event)
            if gap is not None and gap > self._max_gap_seconds:
                boundaries.append((segment_start, previous["frame_index"]))
                segment_start = event["frame_index"]
            previous = event

        boundaries.append((segment_start, previous["frame_index"]))
        return boundaries

    @staticmethod
    def _time_gap(a: dict, b: dict) -> float | None:
        """None (nunca corta ali) se algum dos dois eventos nao tiver
        timestamp - mesma filosofia de "nao decidir sem dado" ja usada em
        outros lugares do Worker (ex.: GoalGeometryAnalyzer)."""
        if a["timestamp_seconds"] is None or b["timestamp_seconds"] is None:
            return None
        return b["timestamp_seconds"] - a["timestamp_seconds"]
