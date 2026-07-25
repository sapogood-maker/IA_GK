"""Testes de worker.perceptual_state.transition_graph.TransitionGraph -
classe genérica, testada independente de qualquer dimensão concreta."""
from __future__ import annotations

import dataclasses

import pytest

from worker.perceptual_state.transition_graph import TransitionGraph


def test_is_legal_true_for_a_pair_in_the_set():
    graph = TransitionGraph(legal_transitions=frozenset({("a", "b")}))
    assert graph.is_legal("a", "b") is True


def test_is_legal_false_for_a_pair_not_in_the_set():
    graph = TransitionGraph(legal_transitions=frozenset({("a", "b")}))
    assert graph.is_legal("b", "a") is False


def test_is_frozen_immutable():
    graph = TransitionGraph(legal_transitions=frozenset())
    with pytest.raises(dataclasses.FrozenInstanceError):
        graph.legal_transitions = frozenset({("x", "y")})  # type: ignore[misc]


def test_empty_graph_permits_nothing():
    graph = TransitionGraph(legal_transitions=frozenset())
    assert graph.is_legal("a", "b") is False
