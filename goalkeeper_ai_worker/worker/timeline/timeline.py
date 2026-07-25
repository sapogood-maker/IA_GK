"""PerceptionTimeline: log imutavel, append-only, de Events (Sprint W28).

Nome revisado de "EventTimeline": esta estrutura deve futuramente
carregar nao so eventos discretos, mas contexto temporal mais amplo da
percepcao (memoria, janelas, agregados - ver PERCEPTION_ENGINE_ARCHITECTURE.md,
Sprints W29/W32) - "Perception" descreve o papel de longo prazo da
estrutura, nao so o que ela guarda hoje.

So `append`/`extend` mutam o estado interno - nao existe `remove`/
`update`/`replace` de proposito: nenhum Event, uma vez adicionado, pode
ser alterado ou removido (reforca a imutabilidade de `Event`, ver
event.py). Combinado, os dois tornam esta estrutura Event-Sourcing
friendly - o estado e 100% reconstruivel reproduzindo a sequencia de
Events, nunca lendo um "estado atual" mutavel.

Deliberadamente SEM API de consulta/filtro/janela temporal
(`filter_by_track`, `last_n_seconds`, etc.) - isso e "Temporal Memory"
(Sprint W32), fora do escopo desta sprint. Aqui so se acumula e se
serializa.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator

from worker.timeline.event import Event


class PerceptionTimeline:
    """Sequencia ordenada (por ordem de insercao) de `Event`s."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def extend(self, events: Iterable[Event]) -> None:
        self._events.extend(events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def to_dict(self) -> list[dict]:
        """Serializa em ordem de `frame_index` (estavel: eventos do mesmo
        frame mantem a ordem em que foram inseridos - `sorted` do Python
        e stable sort)."""
        return [event.to_dict() for event in sorted(self._events, key=lambda e: e.frame_index)]
