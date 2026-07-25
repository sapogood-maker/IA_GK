"""Confirma que worker.memory.content_events.CONTENT_EVENT_TYPES bate,
por VALOR, com o default de GapStrategy (worker/segments/gap_strategy.py)
- risco explicito do documento arquitetural da W32: os dois conjuntos
podem divergir silenciosamente no futuro."""
from __future__ import annotations

from worker.memory.content_events import CONTENT_EVENT_TYPES
from worker.segments.gap_strategy import GapStrategy


def test_matches_gap_strategy_default_content_types():
    gap_strategy_default = GapStrategy()._content_event_types
    assert CONTENT_EVENT_TYPES == gap_strategy_default


def test_is_not_empty():
    assert len(CONTENT_EVENT_TYPES) > 0
