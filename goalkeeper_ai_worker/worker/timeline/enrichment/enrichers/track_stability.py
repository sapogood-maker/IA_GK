"""TrackStabilityEnricher: deriva TrackStable/TrackUnstable a partir da
frequencia de TrackLost/OcclusionDetected de cada track (Sprint W31).

Uma unica passada O(n), estado efemero por track_id (descartado ao
final). `TrackUnstable`: emitido quando o numero de disrupcoes
(TrackLost/OcclusionDetected) dentro de uma janela deslizante
(`window_seconds`) atinge `unstable_threshold_count` - so uma vez por
"episodio" de instabilidade (nao repetido a cada disrupcao subsequente
enquanto a janela continuar cheia). `TrackStable`: emitido quando um
track acumula `stable_duration_seconds` sem nenhuma disrupcao (medido
contra o primeiro `TrackUpdated` visto para aquele track, ou contra a
ultima disrupcao, o que for mais recente).
"""
from __future__ import annotations

from worker.timeline import event_types as timeline_event_types
from worker.timeline.enrichment import event_types as enrichment_event_types
from worker.timeline.enrichment.entity_normalization import normalize_entity_label
from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.provenance import Provenance
from worker.timeline.event import Event

_DISRUPTION_EVENT_TYPES = frozenset({timeline_event_types.TRACK_LOST, timeline_event_types.OCCLUSION_DETECTED})


class TrackStabilityEnricher(Enricher):
    name = "track_stability"

    def __init__(
        self,
        unstable_threshold_count: int = 2,
        window_seconds: float = 5.0,
        stable_duration_seconds: float = 5.0,
    ) -> None:
        self._unstable_threshold_count = unstable_threshold_count
        self._window_seconds = window_seconds
        self._stable_duration_seconds = stable_duration_seconds

    def enrich(self, events: list[dict]) -> list[Event]:
        derived: list[Event] = []

        first_seen_ts: dict[int, float | None] = {}
        disruption_window: dict[int, list[dict]] = {}
        last_disruption_ts: dict[int, float | None] = {}
        unstable_active: dict[int, bool] = {}
        stable_emitted: dict[int, bool] = {}

        for event in events:
            track_id = event["track_id"]
            if track_id is None:
                continue
            if track_id not in first_seen_ts:
                first_seen_ts[track_id] = event["timestamp_seconds"]

            if event["event_type"] in _DISRUPTION_EVENT_TYPES:
                self._handle_disruption(event, track_id, disruption_window, last_disruption_ts, unstable_active, derived)
                stable_emitted[track_id] = False

            elif event["event_type"] == timeline_event_types.TRACK_UPDATED:
                self._handle_update(
                    event, track_id, first_seen_ts, last_disruption_ts, unstable_active, stable_emitted, derived
                )

        return derived

    def _handle_disruption(
        self,
        event: dict,
        track_id: int,
        disruption_window: dict[int, list[dict]],
        last_disruption_ts: dict[int, float | None],
        unstable_active: dict[int, bool],
        derived: list[Event],
    ) -> None:
        timestamp = event["timestamp_seconds"]
        window = disruption_window.setdefault(track_id, [])
        window.append(event)
        if timestamp is not None:
            window[:] = [
                e for e in window if e["timestamp_seconds"] is not None and timestamp - e["timestamp_seconds"] <= self._window_seconds
            ]
            last_disruption_ts[track_id] = timestamp

        if len(window) >= self._unstable_threshold_count and not unstable_active.get(track_id, False):
            provenance = Provenance(source_event_ids=(event["event_id"],))
            derived.append(
                Event(
                    event_type=enrichment_event_types.TRACK_UNSTABLE,
                    frame_index=event["frame_index"],
                    timestamp_seconds=timestamp,
                    track_id=track_id,
                    entity=normalize_entity_label(event["entity"]),
                    position=None,
                    confidence=None,
                    metadata={
                        "disruption_count": len(window),
                        "window_seconds": self._window_seconds,
                        "provenance": list(provenance.source_event_ids),
                    },
                    parent_event_id=provenance.primary_parent_id,
                )
            )
            unstable_active[track_id] = True

    def _handle_update(
        self,
        event: dict,
        track_id: int,
        first_seen_ts: dict[int, float | None],
        last_disruption_ts: dict[int, float | None],
        unstable_active: dict[int, bool],
        stable_emitted: dict[int, bool],
        derived: list[Event],
    ) -> None:
        timestamp = event["timestamp_seconds"]
        since = last_disruption_ts.get(track_id)

        if unstable_active.get(track_id, False) and timestamp is not None and since is not None and (timestamp - since) > self._window_seconds:
            unstable_active[track_id] = False

        if timestamp is None or stable_emitted.get(track_id, False):
            return

        baseline = since if since is not None else first_seen_ts.get(track_id)
        if baseline is None:
            return
        stable_seconds = timestamp - baseline
        if stable_seconds < self._stable_duration_seconds:
            return

        provenance = Provenance(source_event_ids=(event["event_id"],))
        derived.append(
            Event(
                event_type=enrichment_event_types.TRACK_STABLE,
                frame_index=event["frame_index"],
                timestamp_seconds=timestamp,
                track_id=track_id,
                entity=normalize_entity_label(event["entity"]),
                position=None,
                confidence=None,
                metadata={"stable_seconds": stable_seconds, "provenance": list(provenance.source_event_ids)},
                parent_event_id=provenance.primary_parent_id,
            )
        )
        stable_emitted[track_id] = True
