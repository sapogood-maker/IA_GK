"""Testes de worker.perceptual_state.presence_state."""
from __future__ import annotations

from worker.perceptual_state.presence_state import PRESENCE_TRANSITION_GRAPH, PresenceState


def test_present_to_ended_is_legal():
    assert PRESENCE_TRANSITION_GRAPH.is_legal(PresenceState.PRESENT.value, PresenceState.ENDED.value)


def test_ended_to_present_is_not_modeled_this_sprint():
    assert not PRESENCE_TRANSITION_GRAPH.is_legal(PresenceState.ENDED.value, PresenceState.PRESENT.value)


def test_same_state_is_never_legal_no_op_transition():
    assert not PRESENCE_TRANSITION_GRAPH.is_legal(PresenceState.PRESENT.value, PresenceState.PRESENT.value)
