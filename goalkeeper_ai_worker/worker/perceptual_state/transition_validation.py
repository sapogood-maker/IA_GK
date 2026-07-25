"""Validação de transições - responsabilidade SEPARADA de representação
(Sprint W33, ajuste arquitetural aprovado).

Verificar se uma sequência de estados é estruturalmente válida (bate
com o `TransitionGraph`) é uma pergunta DIFERENTE de representar o
estado atual (`TrackState`/`WorkingState`) - por isso vive num módulo
próprio, nunca embutida como campo de `TrackState`. `build_working_state`
nunca chama nada daqui; quem quiser validar, chama explicitamente.

É uma checagem estrutural do MODELO ("esta sequência bate com o grafo
formal?"), nunca uma afirmação sobre o track/entidade em si - equivalente
a um teste de integridade de schema, não uma conclusão comportamental.
"""
from __future__ import annotations

from dataclasses import dataclass

from worker.memory.track_memory import TrackMemory
from worker.perceptual_state.motion_state import MOTION_TRANSITION_GRAPH
from worker.perceptual_state.transition_graph import TransitionGraph


@dataclass(frozen=True)
class TransitionValidationResult:
    track_id: int
    dimension: str
    is_valid: bool
    invalid_pairs: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "dimension": self.dimension,
            "is_valid": self.is_valid,
            "invalid_pairs": [list(pair) for pair in self.invalid_pairs],
        }


def validate_motion_transitions(
    track_memory: TrackMemory, graph: TransitionGraph = MOTION_TRANSITION_GRAPH
) -> TransitionValidationResult:
    """Confere CADA par consecutivo de `track_memory.states_visited`
    contra `graph.is_legal(...)`. Lê `TrackMemory` (TemporalMemory, W32)
    diretamente - independente de `WorkingState` já ter sido construído
    ou não."""
    invalid_pairs: list[tuple[str, str]] = []
    states = track_memory.states_visited
    for previous_state, next_state in zip(states, states[1:]):
        if not graph.is_legal(previous_state, next_state):
            invalid_pairs.append((previous_state, next_state))

    return TransitionValidationResult(
        track_id=track_memory.track_id,
        dimension="motion",
        is_valid=not invalid_pairs,
        invalid_pairs=tuple(invalid_pairs),
    )
