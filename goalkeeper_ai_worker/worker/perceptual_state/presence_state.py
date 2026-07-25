"""PresenceState: vocabulário fechado do eixo de presença (Sprint W33).

Deliberadamente simples - 2 valores. `TemporalMemory` (W32) não expõe
sinal suficiente para reconstruir "perdido e recuperado no meio do
vídeo" (TrackLost/OcclusionDetected não entram em
`worker/memory/content_events.py`) - só a foto final: o track ainda
aparecia no último instante observado, ou parou de aparecer antes
disso. Ver documento arquitetural da W33, Seção 2, para a análise
completa dessa limitação de schema."""
from __future__ import annotations

from enum import Enum

from worker.perceptual_state.transition_graph import TransitionGraph


class PresenceState(str, Enum):
    PRESENT = "present"  # last_seen_timestamp == fim da janela observada
    ENDED = "ended"  # last_seen_timestamp < fim da janela observada


PRESENCE_TRANSITION_GRAPH = TransitionGraph(
    legal_transitions=frozenset({(PresenceState.PRESENT.value, PresenceState.ENDED.value)})
)
