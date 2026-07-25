"""Testes de worker.conviction.conviction_state.ConvictionState."""
from __future__ import annotations

from worker.conviction.conviction_state import ConvictionState


def test_has_exactly_four_values():
    assert {s.value for s in ConvictionState} == {"born", "strengthened", "persisted", "weakened"}


def test_never_has_a_vanished_value():
    """Desaparecer nunca e um valor armazenado - representado por
    ausencia do hypothesis_id no ConvictionSet seguinte."""
    assert "vanished" not in {s.value for s in ConvictionState}
    assert "removed" not in {s.value for s in ConvictionState}
