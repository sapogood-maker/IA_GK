"""Testes de worker.timeline.enrichment.entity_normalization."""
from __future__ import annotations

from worker.timeline.enrichment.entity_normalization import normalize_entity_label


def test_normalizes_sports_ball_to_ball():
    assert normalize_entity_label("sports ball") == "ball"


def test_person_passes_through_unchanged():
    assert normalize_entity_label("person") == "person"


def test_unknown_label_passes_through_without_error():
    assert normalize_entity_label("skateboard") == "skateboard"


def test_none_passes_through_as_none():
    assert normalize_entity_label(None) is None


def test_already_normalized_ball_stays_ball():
    assert normalize_entity_label("ball") == "ball"
