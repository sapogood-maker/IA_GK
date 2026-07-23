"""History: buffer circular genérico com tamanho máximo configurável -
nunca cresce infinitamente.

Reutilizado por `Trajectory` (histórico de posições de um objeto) e pelo
próprio `WorldModel` (histórico recente de `SceneEvent`s do mundo) -
única implementação de "buffer limitado", evita duplicar a lógica de
descarte do item mais antigo em dois lugares."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class History(Generic[T]):
    """Guarda até `max_size` itens - ao exceder, descarta o mais antigo."""

    max_size: int
    _items: deque = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._items = deque(maxlen=self.max_size if self.max_size > 0 else None)

    def add(self, item: T) -> None:
        self._items.append(item)

    def to_list(self) -> list[T]:
        return list(self._items)

    def reset(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
