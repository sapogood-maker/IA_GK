"""Testes de worker.perceptual_state.motion_state."""
from __future__ import annotations

from worker.perceptual_state.motion_state import MOTION_TRANSITION_GRAPH, MotionState


def test_unknown_to_moving_is_legal():
    assert MOTION_TRANSITION_GRAPH.is_legal(MotionState.UNKNOWN.value, MotionState.MOVING.value)


def test_unknown_to_stopped_is_legal():
    assert MOTION_TRANSITION_GRAPH.is_legal(MotionState.UNKNOWN.value, MotionState.STOPPED.value)


def test_moving_to_stopped_and_back_are_legal():
    assert MOTION_TRANSITION_GRAPH.is_legal(MotionState.MOVING.value, MotionState.STOPPED.value)
    assert MOTION_TRANSITION_GRAPH.is_legal(MotionState.STOPPED.value, MotionState.MOVING.value)


def test_same_state_is_never_legal_no_op_transition():
    assert not MOTION_TRANSITION_GRAPH.is_legal(MotionState.MOVING.value, MotionState.MOVING.value)
    assert not MOTION_TRANSITION_GRAPH.is_legal(MotionState.STOPPED.value, MotionState.STOPPED.value)


def test_forgetting_a_known_state_is_impossible():
    assert not MOTION_TRANSITION_GRAPH.is_legal(MotionState.MOVING.value, MotionState.UNKNOWN.value)
    assert not MOTION_TRANSITION_GRAPH.is_legal(MotionState.STOPPED.value, MotionState.UNKNOWN.value)
