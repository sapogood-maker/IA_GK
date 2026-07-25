"""Testes de worker.timeline.enrichment.enrichers.motion_transitions.
MotionTransitionEnricher."""
from __future__ import annotations

from worker.timeline.enrichment.enrichers.motion_transitions import MotionTransitionEnricher
from worker.timeline.enrichment.event_types import (
    BALL_MOTION_STARTED,
    GOALKEEPER_MOVEMENT_STOPPED,
    MOTION_STARTED,
    MOTION_STOPPED,
    OBJECT_STATIONARY,
)


def _scene_event(
    event_id: str,
    event_type: str,
    frame_index: int,
    track_id: int,
    motion_state: str,
    timestamp_seconds: float | None = None,
    entity: str = "person",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds if timestamp_seconds is not None else frame_index * 0.1,
        "track_id": track_id,
        "entity": entity,
        "confidence": None,
        "position": None,
        "metadata": {"motion_state": motion_state, "lifecycle": None, "related_track_id": None},
        "parent_event_id": None,
    }


def test_no_events_produces_no_derived_events():
    enricher = MotionTransitionEnricher()
    assert enricher.enrich([]) == []


def test_first_scene_event_for_a_track_always_emits_a_transition():
    events = [_scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving")]
    derived = MotionTransitionEnricher().enrich(events)
    assert len(derived) == 1
    assert derived[0].event_type == MOTION_STARTED
    assert derived[0].parent_event_id == "e1"
    assert derived[0].track_id == 1


def test_repeated_same_state_does_not_emit_again():
    events = [
        _scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving"),
        _scene_event("e2", "ObjectMoving", 5, track_id=1, motion_state="moving"),
    ]
    derived = MotionTransitionEnricher().enrich(events)
    assert len(derived) == 1  # so a primeira, "moving" -> "moving" nao e transicao


def test_real_transition_emits_motion_stopped():
    events = [
        _scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving"),
        _scene_event("e2", "ObjectStopped", 10, track_id=1, motion_state="stopped"),
    ]
    derived = MotionTransitionEnricher().enrich(events)
    assert [e.event_type for e in derived] == [MOTION_STARTED, MOTION_STOPPED]
    assert derived[1].parent_event_id == "e2"
    assert derived[1].metadata["previous_state"] == "moving"


def test_object_stationary_emitted_after_threshold_on_transition_back_to_moving():
    events = [
        _scene_event("e1", "ObjectStopped", 0, track_id=1, motion_state="stopped", timestamp_seconds=0.0),
        _scene_event("e2", "ObjectMoving", 30, track_id=1, motion_state="moving", timestamp_seconds=3.0),
    ]
    derived = MotionTransitionEnricher(min_stationary_seconds=2.0).enrich(events)
    event_types_seen = [e.event_type for e in derived]
    assert MOTION_STARTED in event_types_seen
    assert OBJECT_STATIONARY in event_types_seen
    stationary = next(e for e in derived if e.event_type == OBJECT_STATIONARY)
    assert stationary.metadata["stationary_seconds"] == 3.0


def test_object_stationary_not_emitted_below_threshold():
    events = [
        _scene_event("e1", "ObjectStopped", 0, track_id=1, motion_state="stopped", timestamp_seconds=0.0),
        _scene_event("e2", "ObjectMoving", 5, track_id=1, motion_state="moving", timestamp_seconds=0.5),
    ]
    derived = MotionTransitionEnricher(min_stationary_seconds=2.0).enrich(events)
    assert OBJECT_STATIONARY not in [e.event_type for e in derived]


def test_object_stationary_trailing_case_track_never_moves_again():
    """Track fica STOPPED ate o fim de events, sem transicao de volta -
    ainda assim deve emitir ObjectStationary, usando o ultimo timestamp
    disponivel como referencia (ver docstring do metodo _trailing_stationary_events)."""
    events = [
        _scene_event("e1", "ObjectStopped", 0, track_id=1, motion_state="stopped", timestamp_seconds=0.0),
        _scene_event("e2", "FrameProcessed", 50, track_id=None, motion_state="unknown", timestamp_seconds=5.0),
    ]
    derived = MotionTransitionEnricher(min_stationary_seconds=2.0).enrich(events)
    stationary = [e for e in derived if e.event_type == OBJECT_STATIONARY]
    assert len(stationary) == 1
    assert stationary[0].metadata["stationary_seconds"] == 5.0
    assert stationary[0].parent_event_id is None  # sem evento de origem unico - ver docstring


def test_entity_filter_restricts_to_matching_normalized_label():
    events = [
        _scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving", entity="sports ball"),
        _scene_event("e2", "ObjectMoving", 0, track_id=2, motion_state="moving", entity="person"),
    ]
    ball_derived = MotionTransitionEnricher(entity_filter="ball").enrich(events)
    assert len(ball_derived) == 1
    assert ball_derived[0].event_type == BALL_MOTION_STARTED
    assert ball_derived[0].track_id == 1


def test_entity_filter_goalkeeper_uses_its_own_event_type():
    events = [
        _scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving", entity="goalkeeper"),
        _scene_event("e2", "ObjectStopped", 10, track_id=1, motion_state="stopped", entity="goalkeeper"),
    ]
    derived = MotionTransitionEnricher(entity_filter="goalkeeper").enrich(events)
    assert derived[-1].event_type == GOALKEEPER_MOVEMENT_STOPPED


def test_multiple_tracks_are_processed_independently():
    events = [
        _scene_event("e1", "ObjectMoving", 0, track_id=1, motion_state="moving"),
        _scene_event("e2", "ObjectMoving", 0, track_id=2, motion_state="moving"),
        _scene_event("e3", "ObjectStopped", 5, track_id=1, motion_state="stopped"),
    ]
    derived = MotionTransitionEnricher().enrich(events)
    track_1_events = [e for e in derived if e.track_id == 1]
    track_2_events = [e for e in derived if e.track_id == 2]
    assert len(track_1_events) == 2  # started + stopped
    assert len(track_2_events) == 1  # so started


def test_events_without_track_id_are_ignored():
    events = [_scene_event("e1", "ObjectMoving", 0, track_id=None, motion_state="moving")]
    assert MotionTransitionEnricher().enrich(events) == []


def test_unrelated_event_types_are_ignored():
    events = [
        {
            "event_id": "e1",
            "event_type": "FrameProcessed",
            "frame_index": 0,
            "timestamp_seconds": 0.0,
            "track_id": None,
            "entity": None,
            "confidence": None,
            "position": None,
            "metadata": {},
            "parent_event_id": None,
        }
    ]
    assert MotionTransitionEnricher().enrich(events) == []
