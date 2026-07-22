"""InferenceStage: delega o processamento ao InferenceEngine configurado.

Substitui completamente o antigo FakeProcessingStage (e o antigo
GenerateArtifactStage, cuja responsabilidade o motor de inferencia agora
absorve). Nenhuma Stage conhece OpenCV/YOLO/PyTorch - so o contrato
InferenceEngine.process(state) (AI_WORKER_CONSTITUTION.md, Secao 6).
"""
from __future__ import annotations

from worker.inference.base import InferenceEngine
from worker.state.pipeline_state import PipelineState


class InferenceStage:
    """Unica responsabilidade: chamar o InferenceEngine ativo."""

    def __init__(self, engine: InferenceEngine) -> None:
        self._engine = engine

    async def run(self, state: PipelineState) -> PipelineState:
        return await self._engine.process(state)
