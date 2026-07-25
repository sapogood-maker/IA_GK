"""Testes de worker.perceptual_state.builder.build_working_state - o
essencial da Sprint W33. So representacao (nenhuma validacao aqui - ver
test_transition_validation.py)."""
from __future__ import annotations

from worker.memory.entity_memory import EntityMemory
from worker.memory.temporal_memory import TemporalMemory
from worker.memory.track_memory import TrackMemory
from worker.perceptual_state.builder import build_working_state
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.presence_state import PresenceState


def _track_memory(**overrides) -> TrackMemory:
    defaults = dict(
        track_id=1,
        entity="ball",
        first_seen_frame=0,
        first_seen_timestamp=0.0,
        last_seen_frame=100,
        last_seen_timestamp=10.0,
        age_seconds=10.0,
        current_motion_state="stopped",
        states_visited=("moving", "stopped"),
        motion_transition_count=2,
        recovery_count=1,
        last_change_frame=100,
        last_change_timestamp=10.0,
    )
    defaults.update(overrides)
    return TrackMemory(**defaults)


def test_empty_memory_produces_empty_working_state():
    memory = TemporalMemory()
    state = build_working_state(memory)
    assert state.track_states == {}
    assert state.entity_states == {}
    assert state.source_track_count == 0


def test_single_state_visited_produces_no_last_transition():
    track_memory = _track_memory(states_visited=("moving",))
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    state = build_working_state(memory)
    assert state.track_states[1].last_motion_transition is None


def test_two_or_more_states_visited_produces_last_transition():
    track_memory = _track_memory(states_visited=("moving", "stopped"))
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    transition = build_working_state(memory).track_states[1].last_motion_transition
    assert transition is not None
    assert transition.from_state == "moving"
    assert transition.to_state == "stopped"
    assert transition.timestamp_seconds == 10.0


def test_motion_state_duration_measured_against_window_end():
    track_memory = _track_memory(last_change_timestamp=6.0)
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    track_state = build_working_state(memory).track_states[1]
    assert track_state.motion_state_duration_seconds == 4.0  # 10.0 (fim da janela) - 6.0


def test_presence_is_present_when_last_seen_frame_equals_window_end():
    track_memory = _track_memory(last_seen_frame=100)
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    track_state = build_working_state(memory).track_states[1]
    assert track_state.presence_state == PresenceState.PRESENT
    assert track_state.time_since_last_seen_seconds == 0.0
    assert track_state.presence_transition is None


def test_presence_is_ended_when_last_seen_frame_before_window_end():
    track_memory = _track_memory(last_seen_frame=50, last_seen_timestamp=5.0)
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    track_state = build_working_state(memory).track_states[1]
    assert track_state.presence_state == PresenceState.ENDED
    assert track_state.time_since_last_seen_seconds == 5.0  # 10.0 - 5.0
    assert track_state.presence_transition is not None
    assert track_state.presence_transition.from_state == "present"
    assert track_state.presence_transition.to_state == "ended"


def test_current_motion_state_none_maps_to_unknown():
    track_memory = _track_memory(current_motion_state=None, states_visited=())
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    assert build_working_state(memory).track_states[1].motion_state == MotionState.UNKNOWN


def test_recovery_count_and_transition_count_are_copied_not_recomputed():
    track_memory = _track_memory(recovery_count=7, motion_transition_count=42)
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    track_state = build_working_state(memory).track_states[1]
    assert track_state.recovery_count == 7
    assert track_state.motion_transition_count == 42


def test_entity_state_aggregates_active_and_ended_tracks():
    present_track = _track_memory(track_id=1, entity="ball", last_seen_frame=100, current_motion_state="moving")
    ended_track = _track_memory(track_id=2, entity="ball", last_seen_frame=50, current_motion_state="stopped")
    memory = TemporalMemory(
        track_memories={1: present_track, 2: ended_track},
        entity_memories={
            "ball": EntityMemory(
                entity="ball", track_ids=frozenset({1, 2}), first_seen_timestamp=0.0, last_seen_timestamp=10.0
            )
        },
        frame_range=(0, 100),
        time_range_seconds=(0.0, 10.0),
    )
    entity_state = build_working_state(memory).entity_states["ball"]
    assert entity_state.active_track_ids == frozenset({1})
    assert entity_state.ended_track_ids == frozenset({2})
    assert entity_state.motion_state_counts == {"moving": 1, "stopped": 1}


def test_determinism_same_input_produces_same_output():
    track_memory = _track_memory()
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))
    first = build_working_state(memory).to_dict()
    second = build_working_state(memory).to_dict()
    assert first == second
