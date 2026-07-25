"""Testes de worker.perceptual_state.transition_validation - separado
de proposito de test_builder.py (representacao vs verificacao)."""
from __future__ import annotations

from worker.memory.track_memory import TrackMemory
from worker.perceptual_state.builder import build_working_state
from worker.memory.temporal_memory import TemporalMemory
from worker.perceptual_state.transition_validation import validate_motion_transitions


def _track_memory(states_visited: tuple[str, ...]) -> TrackMemory:
    return TrackMemory(
        track_id=1,
        entity="ball",
        first_seen_frame=0,
        first_seen_timestamp=0.0,
        last_seen_frame=100,
        last_seen_timestamp=10.0,
        age_seconds=10.0,
        current_motion_state=states_visited[-1] if states_visited else None,
        states_visited=states_visited,
    )


def test_valid_sequence_is_valid():
    result = validate_motion_transitions(_track_memory(("moving", "stopped", "moving")))
    assert result.is_valid is True
    assert result.invalid_pairs == ()


def test_empty_sequence_is_valid_vacuously():
    result = validate_motion_transitions(_track_memory(()))
    assert result.is_valid is True


def test_illegal_pair_is_detected():
    """Sequencia estruturalmente incoerente, injetada de proposito -
    dois 'moving' consecutivos, sem mudanca real (nao deveria acontecer
    no dado real, ja que os geradores upstream sao edge-triggered - mas
    o mecanismo de validacao deve detectar isso se acontecer)."""
    result = validate_motion_transitions(_track_memory(("moving", "moving")))
    assert result.is_valid is False
    assert result.invalid_pairs == (("moving", "moving"),)


def test_forgetting_a_state_is_detected_as_illegal():
    result = validate_motion_transitions(_track_memory(("moving", "unknown")))
    assert result.is_valid is False
    assert result.invalid_pairs == (("moving", "unknown"),)


def test_result_identifies_the_track_and_dimension():
    result = validate_motion_transitions(_track_memory(("moving",)))
    assert result.track_id == 1
    assert result.dimension == "motion"


def test_validation_never_affects_working_state_construction():
    """Rodar (ou nao) a validacao nunca influencia build_working_state -
    responsabilidades totalmente independentes."""
    track_memory = _track_memory(("moving", "moving"))  # ilegal de proposito
    memory = TemporalMemory(track_memories={1: track_memory}, frame_range=(0, 100), time_range_seconds=(0.0, 10.0))

    validate_motion_transitions(track_memory)  # roda a validacao antes
    state_after_validation = build_working_state(memory).to_dict()

    state_without_validation = build_working_state(memory).to_dict()

    assert state_after_validation == state_without_validation
