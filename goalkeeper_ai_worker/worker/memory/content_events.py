"""Conjunto de tipos de evento "relevantes" (Sprint W32) - usado para
decidir o que vira `last_relevant_event` em `TrackMemory`/`EntityMemory`.

Replica, como constante LITERAL, o mesmo conjunto de
`worker/segments/gap_strategy.py::_DEFAULT_CONTENT_EVENT_TYPES` - essa
constante e privada daquele modulo, e `worker/segments/` esta na lista
do que nao pode ser alterado nesta sprint (nao da para torna-la
publica). Mesmo principio ja usado em `PROCESSING_JOBS_STREAM` (W7/W28,
Boundary Enforcement): contrato replicado como literal entre duas partes
que nao podem compartilhar codigo diretamente, nunca importado. Se
`worker/segments/` um dia expuser isso publicamente, os dois conjuntos
podem convergir - decisao de uma sprint futura.

Testado explicitamente (tests/memory/test_content_events.py) contra o
valor real de `GapStrategy` para detectar divergencia silenciosa.
"""
from __future__ import annotations

from worker.timeline import event_types

CONTENT_EVENT_TYPES = frozenset(
    {
        event_types.OBJECT_DETECTED,
        event_types.TRACK_STARTED,
        event_types.TRACK_UPDATED,
        event_types.TRACK_RECOVERED,
    }
)
