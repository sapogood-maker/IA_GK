"""Testes de worker.perceptual_state.entity_state.EntityState."""
from __future__ import annotations

import dataclasses

import pytest

from worker.perceptual_state.entity_state import EntityState


def test_is_frozen_immutable():
    state = EntityState(entity="ball")
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.entity = "person"  # type: ignore[misc]


def test_defaults_produce_empty_state_not_errors():
    state = EntityState(entity="ball")
    payload = state.to_dict()
    assert payload["active_track_ids"] == []
    assert payload["ended_track_ids"] == []
    assert payload["motion_state_counts"] == {}


def test_to_dict_sorts_track_ids_and_counts():
    state = EntityState(
        entity="ball",
        active_track_ids=frozenset({3, 1}),
        ended_track_ids=frozenset({2}),
        motion_state_counts={"stopped": 1, "moving": 2},
    )
    payload = state.to_dict()
    assert payload["active_track_ids"] == [1, 3]
    assert payload["ended_track_ids"] == [2]
    assert list(payload["motion_state_counts"].keys()) == ["moving", "stopped"]


def test_never_has_a_dominant_state_field():
    """So contagem factual - nunca um 'estado dominante' (interpretacao)."""
    field_names = {f.name for f in dataclasses.fields(EntityState)}
    assert not any("dominant" in name for name in field_names)
