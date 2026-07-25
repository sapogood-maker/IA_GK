"""Testes de worker.memory.builder.build_temporal_memory - o essencial
da Sprint W32. Todos sinteticos (sem video/YOLO/Redis)."""
from __future__ import annotations

from worker.memory.builder import build_temporal_memory
from worker.segments.play_segment import PlaySegment


def _raw_event(
    event_id: str,
    event_type: str,
    frame_index: int,
    timestamp_seconds: float | None = None,
    track_id: int | None = None,
    entity: str | None = None,
    motion_state: str | None = None,
    parent_event_id: str | None = None,
) -> dict:
    metadata: dict = {}
    if motion_state is not None:
        metadata["motion_state"] = motion_state
    return {
        "event_id": event_id,
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds if timestamp_seconds is not None else frame_index * 0.1,
        "track_id": track_id,
        "entity": entity,
        "confidence": None,
        "position": None,
        "metadata": metadata,
        "parent_event_id": parent_event_id,
    }


def _derived_motion_event(
    event_id: str,
    event_type: str,
    frame_index: int,
    track_id: int,
    timestamp_seconds: float,
    previous_state: str | None,
    seconds_in_previous_state: float | None,
    parent_event_id: str,
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
        "metadata": {"previous_state": previous_state, "seconds_in_previous_state": seconds_in_previous_state},
        "parent_event_id": parent_event_id,
    }


def test_empty_events_produce_empty_memory():
    memory = build_temporal_memory([])
    assert memory.track_memories == {}
    assert memory.entity_memories == {}
    assert memory.source_event_count == 0


def test_single_raw_transition_updates_track_state():
    events = [_raw_event("e1", "ObjectMoving", 0, timestamp_seconds=0.0, track_id=1, motion_state="moving")]
    memory = build_temporal_memory(events)
    track = memory.track_memories[1]
    assert track.current_motion_state == "moving"
    assert track.motion_transition_count == 1
    assert track.states_visited == ("moving",)


def test_raw_transitions_accumulate_duration_in_previous_state():
    events = [
        _raw_event("e1", "ObjectStopped", 0, timestamp_seconds=0.0, track_id=1, motion_state="stopped"),
        _raw_event("e2", "ObjectMoving", 30, timestamp_seconds=3.0, track_id=1, motion_state="moving"),
        _raw_event("e3", "ObjectStopped", 50, timestamp_seconds=5.0, track_id=1, motion_state="stopped"),
    ]
    memory = build_temporal_memory(events)
    track = memory.track_memories[1]
    assert track.motion_state_durations["stopped"] == 3.0  # e1 -> e2 (0.0 a 3.0)
    assert track.motion_state_durations["moving"] == 2.0  # e2 -> e3 (3.0 a 5.0)
    assert track.states_visited == ("stopped", "moving", "stopped")
    assert track.motion_transition_count == 3


def test_derived_events_use_precomputed_duration_not_recompute():
    events = [
        _derived_motion_event(
            "d1", "MotionStopped", 10, track_id=1, timestamp_seconds=1.0,
            previous_state="moving", seconds_in_previous_state=1.0, parent_event_id="raw1",
        ),
    ]
    memory = build_temporal_memory(events)
    track = memory.track_memories[1]
    assert track.motion_state_durations["moving"] == 1.0
    assert track.current_motion_state == "stopped"


def test_mixed_raw_and_derived_does_not_double_count():
    """raw1 (ObjectStopped) tem um MotionStopped derivado apontando pra
    ele via parent_event_id - o builder deve ignorar raw1 e usar so o
    derivado."""
    events = [
        _raw_event("raw0", "ObjectMoving", 0, timestamp_seconds=0.0, track_id=1, motion_state="moving"),
        _raw_event("raw1", "ObjectStopped", 10, timestamp_seconds=1.0, track_id=1, motion_state="stopped"),
        _derived_motion_event(
            "d1", "MotionStopped", 10, track_id=1, timestamp_seconds=1.0,
            previous_state="moving", seconds_in_previous_state=1.0, parent_event_id="raw1",
        ),
    ]
    memory = build_temporal_memory(events)
    track = memory.track_memories[1]
    # Sem a deduplicacao, contaria raw0->raw1 (via raw) E raw0->d1 (via
    # derivado) = 2 transicoes/2x a duracao. Com dedup: so 2 transicoes
    # no total (raw0 sozinho, depois d1), nunca 3.
    assert track.motion_transition_count == 2
    assert track.motion_state_durations["moving"] == 1.0  # nao 2.0 (duplicado)


def test_recovery_count_via_raw_track_recovered():
    events = [_raw_event("e1", "TrackRecovered", 0, track_id=1, entity="person")]
    memory = build_temporal_memory(events)
    assert memory.track_memories[1].recovery_count == 1


def test_recovery_count_via_derived_does_not_double_count_raw():
    events = [
        _raw_event("raw1", "TrackRecovered", 0, timestamp_seconds=0.0, track_id=1, entity="ball"),
        {
            "event_id": "d1",
            "event_type": "TrackRecoveredWithConfidence",
            "frame_index": 0,
            "timestamp_seconds": 0.0,
            "track_id": 1,
            "entity": "ball",
            "confidence": 0.8,
            "position": None,
            "metadata": {},
            "parent_event_id": "raw1",
        },
    ]
    memory = build_temporal_memory(events)
    assert memory.track_memories[1].recovery_count == 1  # nao 2


def test_last_relevant_event_is_a_compact_reference():
    events = [
        _raw_event("e1", "ObjectDetected", 0, track_id=None, entity="ball"),
        _raw_event("e2", "TrackStarted", 0, track_id=1, entity="ball"),
        _raw_event("e3", "TrackUpdated", 10, track_id=1, entity="ball"),
    ]
    memory = build_temporal_memory(events)
    reference = memory.track_memories[1].last_relevant_event
    assert reference is not None
    assert reference.event_id == "e3"
    assert reference.event_type == "TrackUpdated"


def test_events_not_in_content_types_do_not_update_last_relevant_event():
    events = [
        _raw_event("e1", "TrackStarted", 0, track_id=1, entity="ball"),
        _raw_event("e2", "OcclusionDetected", 5, track_id=1, entity="ball"),
    ]
    memory = build_temporal_memory(events)
    assert memory.track_memories[1].last_relevant_event.event_id == "e1"


def test_multiple_tracks_are_independent():
    events = [
        _raw_event("e1", "ObjectMoving", 0, timestamp_seconds=0.0, track_id=1, motion_state="moving"),
        _raw_event("e2", "ObjectStopped", 0, timestamp_seconds=0.0, track_id=2, motion_state="stopped"),
    ]
    memory = build_temporal_memory(events)
    assert memory.track_memories[1].current_motion_state == "moving"
    assert memory.track_memories[2].current_motion_state == "stopped"


def test_entity_memory_aggregates_across_track_ids_with_normalization():
    """track 1 e track 2 tem rotulos diferentes ('sports ball' bruto vs
    'ball' normalizado) mas devem cair na MESMA EntityMemory."""
    events = [
        _raw_event("e1", "ObjectMoving", 0, timestamp_seconds=0.0, track_id=1, entity="sports ball", motion_state="moving"),
        _raw_event("e2", "ObjectStopped", 10, timestamp_seconds=1.0, track_id=1, entity="sports ball", motion_state="stopped"),
        _raw_event("e3", "ObjectMoving", 20, timestamp_seconds=2.0, track_id=2, entity="ball", motion_state="moving"),
    ]
    memory = build_temporal_memory(events)
    assert set(memory.entity_memories.keys()) == {"ball"}
    assert memory.entity_memories["ball"].track_ids == frozenset({1, 2})


def test_entity_memory_combines_recovery_counts_from_its_tracks():
    events = [
        _raw_event("e1", "TrackRecovered", 0, track_id=1, entity="ball"),
        _raw_event("e2", "TrackRecovered", 10, track_id=2, entity="ball"),
    ]
    memory = build_temporal_memory(events)
    assert memory.entity_memories["ball"].total_recovery_count == 2


def test_first_and_last_seen_and_age():
    events = [
        _raw_event("e1", "TrackStarted", 0, timestamp_seconds=0.0, track_id=1, entity="ball"),
        _raw_event("e2", "TrackUpdated", 100, timestamp_seconds=10.0, track_id=1, entity="ball"),
    ]
    memory = build_temporal_memory(events)
    track = memory.track_memories[1]
    assert track.first_seen_frame == 0
    assert track.last_seen_frame == 100
    assert track.age_seconds == 10.0


def test_frame_range_and_time_range_cover_all_events_not_just_track_events():
    events = [
        _raw_event("e0", "FrameProcessed", 0, timestamp_seconds=0.0, track_id=None),
        _raw_event("e1", "TrackStarted", 5, timestamp_seconds=0.5, track_id=1, entity="ball"),
        _raw_event("e2", "FrameProcessed", 568, timestamp_seconds=18.9, track_id=None),
    ]
    memory = build_temporal_memory(events)
    assert memory.frame_range == (0, 568)
    assert memory.time_range_seconds == (0.0, 18.9)
    assert memory.source_event_count == 3


def test_determinism_same_input_produces_same_output():
    events = [
        _raw_event("e1", "ObjectMoving", 0, timestamp_seconds=0.0, track_id=1, entity="ball", motion_state="moving"),
        _raw_event("e2", "ObjectStopped", 10, timestamp_seconds=1.0, track_id=1, entity="ball", motion_state="stopped"),
    ]
    first = build_temporal_memory(events).to_dict()
    second = build_temporal_memory(events).to_dict()
    assert first == second


def test_cross_check_against_play_segment_track_ids():
    """Reuso concreto de PlaySegment (documento arquitetural, Secao 8):
    os track_id de TemporalMemory devem bater com PlaySegment.track_ids
    quando construidos a partir dos MESMOS eventos."""
    events = [
        _raw_event("e1", "TrackStarted", 0, timestamp_seconds=0.0, track_id=1, entity="person"),
        _raw_event("e2", "TrackStarted", 0, timestamp_seconds=0.0, track_id=2, entity="ball"),
    ]
    segment = PlaySegment(
        segment_id="seg-1",
        start_frame=0,
        end_frame=0,
        start_timestamp=0.0,
        end_timestamp=0.0,
        duration_seconds=0.0,
        track_ids=frozenset({1, 2}),
        ball_involved=True,
        events=events,
    )
    memory = build_temporal_memory(segment.events)
    assert set(memory.track_memories.keys()) == segment.track_ids
