"""MotionTransitionEnricher: deriva MotionStarted/MotionStopped/
ObjectStationary a partir de ObjectMoving/ObjectStopped (Sprint W31).

Uma unica passada O(n) sobre `events`, mantendo um dict efemero
`{track_id: ...}` (descartado ao final da chamada - nunca persiste entre
chamadas, nunca compartilhado com outro Enricher). Determinismo: mesma
entrada, mesma sequencia de saida, sempre - nenhuma dependencia de
iteracao de set/dict sem chave estavel.

`entity_filter` parametriza a MESMA classe para produzir
BallMotionStarted/Stopped ou GoalkeeperMovementStarted/Stopped em vez do
tipo generico MotionStarted/Stopped - nao sao classes separadas (ver
worker/timeline/enrichment/event_types.py, MOTION_EVENT_TYPES_BY_ENTITY).
"""
from __future__ import annotations

from worker.timeline import event_types as timeline_event_types
from worker.timeline.enrichment import event_types as enrichment_event_types
from worker.timeline.enrichment.entity_normalization import normalize_entity_label
from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.provenance import Provenance
from worker.timeline.event import Event

_MOVING = "moving"
_STOPPED = "stopped"

_CONTENT_EVENT_TYPES = frozenset({timeline_event_types.OBJECT_MOVING, timeline_event_types.OBJECT_STOPPED})


class MotionTransitionEnricher(Enricher):
    name = "motion_transitions"

    def __init__(
        self,
        entity_filter: str | None = None,
        min_stationary_seconds: float = 2.0,
    ) -> None:
        self._entity_filter = entity_filter
        self._min_stationary_seconds = min_stationary_seconds
        self._started_type, self._stopped_type = enrichment_event_types.MOTION_EVENT_TYPES_BY_ENTITY.get(
            entity_filter, enrichment_event_types.DEFAULT_MOTION_EVENT_TYPES
        )

    def enrich(self, events: list[dict]) -> list[Event]:
        derived: list[Event] = []
        # Estado efemero, uma chamada = uma passada, descartado ao sair.
        last_state: dict[int, str] = {}
        since_timestamp: dict[int, float | None] = {}

        for event in events:
            if event["event_type"] not in _CONTENT_EVENT_TYPES:
                continue
            track_id = event["track_id"]
            if track_id is None:
                continue

            normalized_entity = normalize_entity_label(event["entity"])
            if self._entity_filter is not None and normalized_entity != self._entity_filter:
                continue

            new_state = event["metadata"].get("motion_state")
            previous_state = last_state.get(track_id)
            previous_ts = since_timestamp.get(track_id)
            current_ts = event["timestamp_seconds"]

            if previous_state != new_state:
                seconds_in_previous_state = (
                    current_ts - previous_ts
                    if previous_ts is not None and current_ts is not None
                    else None
                )
                event_type = self._stopped_type if new_state == _STOPPED else self._started_type

                provenance = Provenance(source_event_ids=(event["event_id"],))
                derived.append(
                    Event(
                        event_type=event_type,
                        frame_index=event["frame_index"],
                        timestamp_seconds=current_ts,
                        track_id=track_id,
                        entity=normalized_entity,
                        position=None,
                        confidence=None,
                        metadata={
                            "previous_state": previous_state,
                            "seconds_in_previous_state": seconds_in_previous_state,
                            "provenance": list(provenance.source_event_ids),
                        },
                        parent_event_id=provenance.primary_parent_id,
                    )
                )

                # ObjectStationary: emitido junto da transicao STOPPED -> MOVING
                # (e o unico momento em que a duracao do periodo parado e
                # conhecida com certeza) se essa duracao passou do limiar.
                if (
                    previous_state == _STOPPED
                    and new_state == _MOVING
                    and seconds_in_previous_state is not None
                    and seconds_in_previous_state >= self._min_stationary_seconds
                ):
                    stationary_provenance = Provenance(source_event_ids=(event["event_id"],))
                    derived.append(
                        Event(
                            event_type=enrichment_event_types.OBJECT_STATIONARY,
                            frame_index=event["frame_index"],
                            timestamp_seconds=current_ts,
                            track_id=track_id,
                            entity=normalized_entity,
                            position=None,
                            confidence=None,
                            metadata={
                                "stationary_seconds": seconds_in_previous_state,
                                "provenance": list(stationary_provenance.source_event_ids),
                            },
                            parent_event_id=stationary_provenance.primary_parent_id,
                        )
                    )

                last_state[track_id] = new_state
                since_timestamp[track_id] = current_ts

        derived.extend(self._trailing_stationary_events(events, last_state, since_timestamp))
        return derived

    def _trailing_stationary_events(
        self,
        events: list[dict],
        last_state: dict[int, str],
        since_timestamp: dict[int, float | None],
    ) -> list[Event]:
        """Um track que fica STOPPED ate o fim de `events` (sem nunca
        transicionar de volta para MOVING) nunca teria seu tempo parado
        contabilizado pelo laco principal (que so sabe a duracao no
        momento da transicao de SAIDA do estado). Usa o timestamp do
        ULTIMO evento de `events` como "agora" de referencia - unica
        forma de dar fechamento a esse caso sem inventar um relogio
        externo, e ainda determinístico (funcao pura da mesma entrada)."""
        last_timestamp: float | None = None
        last_frame_index: int | None = None
        for e in reversed(events):
            if e["timestamp_seconds"] is not None:
                last_timestamp = e["timestamp_seconds"]
                last_frame_index = e["frame_index"]
                break
        if last_timestamp is None:
            return []

        trailing: list[Event] = []
        for track_id, state in last_state.items():
            if state != _STOPPED:
                continue
            started_ts = since_timestamp.get(track_id)
            if started_ts is None:
                continue
            stationary_seconds = last_timestamp - started_ts
            if stationary_seconds < self._min_stationary_seconds:
                continue

            trailing.append(
                Event(
                    event_type=enrichment_event_types.OBJECT_STATIONARY,
                    frame_index=last_frame_index,
                    timestamp_seconds=last_timestamp,
                    track_id=track_id,
                    entity=None,
                    position=None,
                    confidence=None,
                    metadata={"stationary_seconds": stationary_seconds, "provenance": []},
                    parent_event_id=None,
                )
            )
        return trailing
