"""build_temporal_memory: constroi uma TemporalMemory a partir de uma
sequencia de eventos ja cronologica (Sprint W32).

Uma unica passagem O(n) sobre `events` para tudo que exige ler cada
evento (first/last seen, transicoes de motion_state, recuperacoes,
ultimo evento relevante por track E por entidade - agregacao por
entidade e barata o bastante para acontecer na MESMA passagem, "ultimo
vence" funciona de graca porque `events` ja e cronologico). Uma segunda
passagem, muito mais barata (O(numero de tracks), nao O(numero de
eventos)), soma os campos ja calculados de cada TrackMemory por
`entity` para produzir `combined_motion_state_durations`/
`total_recovery_count` de EntityMemory - evita duplicar a logica de
deteccao de transicao/deduplicacao (Secao 7 do documento arquitetural)
uma segunda vez, sem violar o principio de O(n) geral (tracks sao muito
menos numerosos que eventos - 48 tracks para 34 mil eventos no artifact
real da W28).

`events` pode misturar eventos BRUTOS (W28: ObjectMoving/ObjectStopped/
TrackRecovered) e DERIVADOS (W31: MotionStarted/Stopped/BallMotion*/
GoalkeeperMovement*/TrackRecoveredWithConfidence) - ambos sao dicts no
MESMO formato (`Event.to_dict()`), consequencia direta da W31 ter
reusado a classe Event em vez de um schema paralelo. Quando um evento
bruto tem um evento derivado correspondente (via `parent_event_id`) no
MESMO `events`, o bruto e ignorado para fins de contagem/duracao (nunca
conta a mesma transicao duas vezes) - mas o derivado usa os campos que
o Enricher ja calculou (`seconds_in_previous_state`), nunca recalcula.
"""
from __future__ import annotations

from worker.memory.content_events import CONTENT_EVENT_TYPES
from worker.memory.entity_memory import EntityMemory
from worker.memory.event_reference import EventReference
from worker.memory.temporal_memory import TemporalMemory
from worker.memory.track_memory import TrackMemory
from worker.timeline import event_types as timeline_event_types
from worker.timeline.enrichment import event_types as enrichment_event_types
from worker.timeline.enrichment.entity_normalization import normalize_entity_label

_MOVING = "moving"
_STOPPED = "stopped"

_RAW_MOTION_TYPES = frozenset({timeline_event_types.OBJECT_MOVING, timeline_event_types.OBJECT_STOPPED})
_DERIVED_STARTED_TYPES = frozenset(
    {
        enrichment_event_types.MOTION_STARTED,
        enrichment_event_types.BALL_MOTION_STARTED,
        enrichment_event_types.GOALKEEPER_MOVEMENT_STARTED,
    }
)
_DERIVED_STOPPED_TYPES = frozenset(
    {
        enrichment_event_types.MOTION_STOPPED,
        enrichment_event_types.BALL_MOTION_STOPPED,
        enrichment_event_types.GOALKEEPER_MOVEMENT_STOPPED,
    }
)
_DERIVED_MOTION_TYPES = _DERIVED_STARTED_TYPES | _DERIVED_STOPPED_TYPES

_RAW_RECOVERY_TYPE = timeline_event_types.TRACK_RECOVERED
_DERIVED_RECOVERY_TYPE = enrichment_event_types.TRACK_RECOVERED_WITH_CONFIDENCE


def build_temporal_memory(events: list[dict]) -> TemporalMemory:
    superseded_event_ids = _collect_superseded_event_ids(events)

    track_accumulators: dict[int, dict] = {}
    entity_accumulators: dict[str, dict] = {}

    frame_indexes: list[int] = []
    timestamps: list[float] = []

    for event in events:
        frame_indexes.append(event["frame_index"])
        if event["timestamp_seconds"] is not None:
            timestamps.append(event["timestamp_seconds"])

        track_id = event["track_id"]
        if track_id is None:
            continue

        track_acc = track_accumulators.setdefault(track_id, _new_track_accumulator())
        _touch_seen(track_acc, event)

        normalized_entity = normalize_entity_label(event["entity"])
        if normalized_entity is not None:
            track_acc["entity"] = normalized_entity
            entity_acc = entity_accumulators.setdefault(normalized_entity, _new_entity_accumulator())
            entity_acc["track_ids"].add(track_id)
            _touch_seen_entity(entity_acc, event)

        event_type = event["event_type"]

        if event_type in CONTENT_EVENT_TYPES:
            reference = EventReference.from_event(event)
            track_acc["last_relevant_event"] = reference
            if normalized_entity is not None:
                entity_accumulators[normalized_entity]["last_relevant_event"] = reference

        if event_type in _DERIVED_MOTION_TYPES:
            _apply_derived_motion_transition(track_acc, event)
        elif event_type in _RAW_MOTION_TYPES and event["event_id"] not in superseded_event_ids:
            _apply_raw_motion_transition(track_acc, event)

        if event_type == _DERIVED_RECOVERY_TYPE:
            track_acc["recovery_count"] += 1
        elif event_type == _RAW_RECOVERY_TYPE and event["event_id"] not in superseded_event_ids:
            track_acc["recovery_count"] += 1

    track_memories = {track_id: _freeze_track(track_id, acc) for track_id, acc in track_accumulators.items()}
    entity_memories = {
        entity: _freeze_entity(entity, acc, track_memories) for entity, acc in entity_accumulators.items()
    }

    return TemporalMemory(
        track_memories=track_memories,
        entity_memories=entity_memories,
        frame_range=(min(frame_indexes), max(frame_indexes)) if frame_indexes else None,
        time_range_seconds=(min(timestamps), max(timestamps)) if timestamps else None,
        source_event_count=len(events),
    )


def _collect_superseded_event_ids(events: list[dict]) -> frozenset[str]:
    """event_id de todo evento BRUTO que ja tem um evento DERIVADO
    correspondente (via parent_event_id) no mesmo `events` - esses
    brutos sao ignorados para contagem/duracao (nunca conta a mesma
    transicao duas vezes)."""
    superseded = set()
    for event in events:
        is_derived = event["event_type"] in _DERIVED_MOTION_TYPES or event["event_type"] == _DERIVED_RECOVERY_TYPE
        if is_derived and event["parent_event_id"] is not None:
            superseded.add(event["parent_event_id"])
    return frozenset(superseded)


def _new_track_accumulator() -> dict:
    return {
        "entity": None,
        "first_seen_frame": None,
        "first_seen_timestamp": None,
        "last_seen_frame": None,
        "last_seen_timestamp": None,
        "current_motion_state": None,
        "state_since_timestamp": None,
        "motion_state_durations": {},
        "states_visited": [],
        "motion_transition_count": 0,
        "recovery_count": 0,
        "last_change_frame": None,
        "last_change_timestamp": None,
        "last_relevant_event": None,
    }


def _new_entity_accumulator() -> dict:
    return {
        "track_ids": set(),
        "first_seen_timestamp": None,
        "last_seen_timestamp": None,
        "last_relevant_event": None,
    }


def _touch_seen(acc: dict, event: dict) -> None:
    if acc["first_seen_frame"] is None:
        acc["first_seen_frame"] = event["frame_index"]
        acc["first_seen_timestamp"] = event["timestamp_seconds"]
    acc["last_seen_frame"] = event["frame_index"]
    if event["timestamp_seconds"] is not None:
        acc["last_seen_timestamp"] = event["timestamp_seconds"]


def _touch_seen_entity(acc: dict, event: dict) -> None:
    if acc["first_seen_timestamp"] is None:
        acc["first_seen_timestamp"] = event["timestamp_seconds"]
    if event["timestamp_seconds"] is not None:
        acc["last_seen_timestamp"] = event["timestamp_seconds"]


def _apply_derived_motion_transition(acc: dict, event: dict) -> None:
    """MotionStarted/Stopped (W31) ja carrega previous_state/
    seconds_in_previous_state prontos em metadata - so soma, nunca
    recalcula."""
    metadata = event["metadata"]
    previous_state = metadata.get("previous_state")
    seconds_in_previous_state = metadata.get("seconds_in_previous_state")
    new_state = _MOVING if event["event_type"] in _DERIVED_STARTED_TYPES else _STOPPED

    if previous_state is not None and seconds_in_previous_state is not None:
        acc["motion_state_durations"][previous_state] = (
            acc["motion_state_durations"].get(previous_state, 0.0) + seconds_in_previous_state
        )

    acc["states_visited"].append(new_state)
    acc["motion_transition_count"] += 1
    acc["current_motion_state"] = new_state
    acc["last_change_frame"] = event["frame_index"]
    acc["last_change_timestamp"] = event["timestamp_seconds"]


def _apply_raw_motion_transition(acc: dict, event: dict) -> None:
    """Fallback quando a Enrichment (W31) nao rodou - deriva a duracao do
    estado anterior a partir do proprio timestamp do evento bruto
    (ObjectMoving/ObjectStopped, W28)."""
    new_state = event["metadata"].get("motion_state")
    if new_state is None:
        return
    previous_state = acc["current_motion_state"]
    if previous_state == new_state:
        return  # SceneAnalyzer ja emite esses eventos so em transicao real

    if previous_state is not None and acc["state_since_timestamp"] is not None and event["timestamp_seconds"] is not None:
        duration = event["timestamp_seconds"] - acc["state_since_timestamp"]
        acc["motion_state_durations"][previous_state] = acc["motion_state_durations"].get(previous_state, 0.0) + duration

    acc["states_visited"].append(new_state)
    acc["motion_transition_count"] += 1
    acc["current_motion_state"] = new_state
    acc["state_since_timestamp"] = event["timestamp_seconds"]
    acc["last_change_frame"] = event["frame_index"]
    acc["last_change_timestamp"] = event["timestamp_seconds"]


def _freeze_track(track_id: int, acc: dict) -> TrackMemory:
    first_ts = acc["first_seen_timestamp"]
    last_ts = acc["last_seen_timestamp"]
    age_seconds = (last_ts - first_ts) if first_ts is not None and last_ts is not None else None

    return TrackMemory(
        track_id=track_id,
        entity=acc["entity"],
        first_seen_frame=acc["first_seen_frame"],
        first_seen_timestamp=first_ts,
        last_seen_frame=acc["last_seen_frame"],
        last_seen_timestamp=last_ts,
        age_seconds=age_seconds,
        current_motion_state=acc["current_motion_state"],
        motion_state_durations=dict(acc["motion_state_durations"]),
        states_visited=tuple(acc["states_visited"]),
        motion_transition_count=acc["motion_transition_count"],
        recovery_count=acc["recovery_count"],
        last_change_frame=acc["last_change_frame"],
        last_change_timestamp=acc["last_change_timestamp"],
        last_relevant_event=acc["last_relevant_event"],
    )


def _freeze_entity(entity: str, acc: dict, track_memories: dict[int, TrackMemory]) -> EntityMemory:
    """combined_motion_state_durations/total_recovery_count somam os
    campos JA calculados de cada TrackMemory deste rotulo - nao
    reprocessa `events` (evita duplicar a logica de deduplicacao
    bruto/derivado uma segunda vez)."""
    combined_durations: dict[str, float] = {}
    total_recovery_count = 0
    for track_id in acc["track_ids"]:
        track_memory = track_memories[track_id]
        total_recovery_count += track_memory.recovery_count
        for state, duration in track_memory.motion_state_durations.items():
            combined_durations[state] = combined_durations.get(state, 0.0) + duration

    return EntityMemory(
        entity=entity,
        track_ids=frozenset(acc["track_ids"]),
        first_seen_timestamp=acc["first_seen_timestamp"],
        last_seen_timestamp=acc["last_seen_timestamp"],
        combined_motion_state_durations=combined_durations,
        total_recovery_count=total_recovery_count,
        last_relevant_event=acc["last_relevant_event"],
    )
