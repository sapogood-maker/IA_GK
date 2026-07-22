"""Interface unica de todo motor de inferencia - InferenceEngine.

Nenhuma Stage do Pipeline conhece OpenCV/YOLO/PyTorch - so conhece
`engine.process(state)`. Implementar esta classe e a unica forma valida
de adicionar um motor novo (AI_WORKER_CONSTITUTION.md, Secao 6).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.state.pipeline_state import PipelineState


class InferenceEngine(ABC):
    """Todo motor de inferencia processa o PipelineState e devolve o mesmo
    PipelineState, com o resultado ja registrado nele."""

    name: str
    version: str

    @abstractmethod
    async def process(self, state: PipelineState) -> PipelineState: ...
