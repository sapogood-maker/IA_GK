"""MotionState: vocabulário fechado do eixo de movimento (Sprint W33).

Reaproveita o vocabulário já estabelecido em W28/W31/W32
("moving"/"stopped"/"unknown", já usado em `TrackMemory.current_motion_state`)
- nenhum conceito novo, só formalizado como `Enum` para dar tipagem
explícita e um `TransitionGraph` próprio."""
from __future__ import annotations

from enum import Enum

from worker.perceptual_state.transition_graph import TransitionGraph


class MotionState(str, Enum):
    UNKNOWN = "unknown"
    MOVING = "moving"
    STOPPED = "stopped"


MOTION_TRANSITION_GRAPH = TransitionGraph(
    legal_transitions=frozenset(
        {
            (MotionState.UNKNOWN.value, MotionState.MOVING.value),
            (MotionState.UNKNOWN.value, MotionState.STOPPED.value),
            (MotionState.MOVING.value, MotionState.STOPPED.value),
            (MotionState.STOPPED.value, MotionState.MOVING.value),
        }
    )
)
