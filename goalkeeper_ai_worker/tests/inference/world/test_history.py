"""Testes de worker.inference.world.history.History - buffer circular
generico, nunca cresce alem de max_size."""
from __future__ import annotations

from worker.inference.world.history import History


def test_history_keeps_items_up_to_max_size() -> None:
    history: History[int] = History(max_size=3)

    for item in (1, 2, 3):
        history.add(item)

    assert history.to_list() == [1, 2, 3]
    assert len(history) == 3


def test_history_discards_oldest_item_beyond_max_size() -> None:
    history: History[int] = History(max_size=3)

    for item in (1, 2, 3, 4, 5):
        history.add(item)

    assert history.to_list() == [3, 4, 5]
    assert len(history) == 3


def test_history_reset_clears_all_items() -> None:
    history: History[int] = History(max_size=3)
    history.add(1)
    history.add(2)

    history.reset()

    assert history.to_list() == []
    assert len(history) == 0
