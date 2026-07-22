"""Testes de InferenceStage - confirma que ela so delega ao motor, sem
nenhuma logica adicional."""
from __future__ import annotations

from worker.inference.base import InferenceEngine
from worker.pipeline.stages.inference import InferenceStage
from worker.state.pipeline_state import PipelineState


class _StubEngine(InferenceEngine):
    name = "stub"
    version = "0.0.0"

    def __init__(self) -> None:
        self.received_state: PipelineState | None = None

    async def process(self, state: PipelineState) -> PipelineState:
        self.received_state = state
        state.status = "STUB_PROCESSED"
        return state


async def test_run_delegates_entirely_to_the_engine(base_state) -> None:
    engine = _StubEngine()
    stage = InferenceStage(engine)

    result = await stage.run(base_state)

    assert engine.received_state is base_state
    assert result.status == "STUB_PROCESSED"
