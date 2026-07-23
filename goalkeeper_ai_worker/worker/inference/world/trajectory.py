"""Trajectory: histórico limitado de posições de um único objeto.

Composição sobre `History` (nunca duplica a lógica de buffer limitado) -
"últimos N pontos", `N` configurável via `WORKER_WORLD_MAX_TRAJECTORY`."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.inference.world.history import History
from worker.inference.world.types import Position


@dataclass
class Trajectory:
    """Histórico de posições de um objeto - nunca cresce além de `max_length`."""

    max_length: int
    _history: History = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._history = History(max_size=self.max_length)

    def add_point(self, position: Position) -> None:
        self._history.add(position)

    @property
    def points(self) -> list[Position]:
        return self._history.to_list()

    def __len__(self) -> int:
        return len(self._history)
