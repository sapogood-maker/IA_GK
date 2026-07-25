"""Testes de worker.conviction.conviction_level.ConvictionLevel/level_for."""
from __future__ import annotations

from worker.conviction.conviction_level import ConvictionLevel, level_for


def test_has_exactly_three_values():
    assert {lv.value for lv in ConvictionLevel} == {"emerging", "stable", "strong"}


def test_emerging_below_stable_threshold():
    assert level_for(0) == ConvictionLevel.EMERGING
    assert level_for(1) == ConvictionLevel.EMERGING
    assert level_for(2) == ConvictionLevel.EMERGING


def test_stable_at_exact_threshold():
    assert level_for(3) == ConvictionLevel.STABLE
    assert level_for(5) == ConvictionLevel.STABLE


def test_strong_at_exact_threshold():
    assert level_for(6) == ConvictionLevel.STRONG
    assert level_for(100) == ConvictionLevel.STRONG
