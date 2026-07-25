"""build_working_state: projeta um WorkingState a partir de uma
TemporalMemory já construída (Sprint W33).

Função pura - recalcula o WorkingState inteiro a cada chamada, do zero.
Não é uma máquina de estados clássica (nenhum objeto que "recebe"
eventos e transita a si mesmo). O(número de tracks + número de
entidades) de `memory` - nunca volta a percorrer os eventos brutos
(esses já foram resumidos por `build_temporal_memory`, W32). Nunca
valida nada por conta própria - ver `transition_validation.py` para a
responsabilidade de verificação, deliberadamente separada.
"""
from __future__ import annotations

from worker.memory.entity_memory import EntityMemory
from worker.memory.temporal_memory import TemporalMemory
from worker.memory.track_memory import TrackMemory
from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.state_transition import StateTransition
from worker.perceptual_state.track_state import TrackState
from worker.perceptual_state.working_state import WorkingState


def build_working_state(memory: TemporalMemory) -> WorkingState:
    now_frame = memory.frame_range[1] if memory.frame_range is not None else None
    now_timestamp = memory.time_range_seconds[1] if memory.time_range_seconds is not None else None

    track_states = {
        track_id: _build_track_state(track_memory, now_frame, now_timestamp)
        for track_id, track_memory in memory.track_memories.items()
    }
    entity_states = {
        entity: _build_entity_state(entity_memory, track_states)
        for entity, entity_memory in memory.entity_memories.items()
    }

    return WorkingState(
        track_states=track_states,
        entity_states=entity_states,
        observed_at_frame=now_frame,
        observed_at_timestamp=now_timestamp,
        source_track_count=len(track_states),
    )


def _build_track_state(track_memory: TrackMemory, now_frame: int | None, now_timestamp: float | None) -> TrackState:
    motion_state = MotionState(track_memory.current_motion_state) if track_memory.current_motion_state else MotionState.UNKNOWN

    motion_state_duration_seconds = None
    if now_timestamp is not None and track_memory.last_change_timestamp is not None:
        motion_state_duration_seconds = now_timestamp - track_memory.last_change_timestamp

    last_motion_transition = None
    if len(track_memory.states_visited) >= 2:
        last_motion_transition = StateTransition(
            dimension="motion",
            from_state=track_memory.states_visited[-2],
            to_state=track_memory.states_visited[-1],
            frame_index=track_memory.last_change_frame,
            timestamp_seconds=track_memory.last_change_timestamp,
        )

    # Presenca decidida por FRAME (sempre presente no schema de Event),
    # nao por timestamp (opcional) - comparacao mais robusta.
    is_present = now_frame is not None and track_memory.last_seen_frame == now_frame
    presence_state = PresenceState.PRESENT if is_present else PresenceState.ENDED

    time_since_last_seen_seconds = None
    if now_timestamp is not None and track_memory.last_seen_timestamp is not None:
        time_since_last_seen_seconds = now_timestamp - track_memory.last_seen_timestamp

    presence_transition = None
    if presence_state == PresenceState.ENDED:
        presence_transition = StateTransition(
            dimension="presence",
            from_state=PresenceState.PRESENT.value,
            to_state=PresenceState.ENDED.value,
            frame_index=track_memory.last_seen_frame,
            timestamp_seconds=track_memory.last_seen_timestamp,
        )

    return TrackState(
        track_id=track_memory.track_id,
        entity=track_memory.entity,
        motion_state=motion_state,
        motion_state_since_timestamp=track_memory.last_change_timestamp,
        motion_state_duration_seconds=motion_state_duration_seconds,
        motion_transition_count=track_memory.motion_transition_count,
        last_motion_transition=last_motion_transition,
        presence_state=presence_state,
        time_since_last_seen_seconds=time_since_last_seen_seconds,
        presence_transition=presence_transition,
        recovery_count=track_memory.recovery_count,
    )


def _build_entity_state(entity_memory: EntityMemory, track_states: dict[int, TrackState]) -> EntityState:
    active_ids: set[int] = set()
    ended_ids: set[int] = set()
    motion_state_counts: dict[str, int] = {}

    for track_id in entity_memory.track_ids:
        track_state = track_states[track_id]
        if track_state.presence_state == PresenceState.PRESENT:
            active_ids.add(track_id)
        else:
            ended_ids.add(track_id)
        motion_value = track_state.motion_state.value
        motion_state_counts[motion_value] = motion_state_counts.get(motion_value, 0) + 1

    return EntityState(
        entity=entity_memory.entity,
        active_track_ids=frozenset(active_ids),
        ended_track_ids=frozenset(ended_ids),
        motion_state_counts=motion_state_counts,
    )
