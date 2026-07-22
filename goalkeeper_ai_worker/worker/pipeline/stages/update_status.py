"""UpdateStatusStage: reporta a conclusao do Job ao backend."""
from __future__ import annotations

from worker.infrastructure.backend_client.client import BackendClient
from worker.state.pipeline_state import PipelineState


class UpdateStatusStage:
    """Unica responsabilidade: atualizar o status do Job para COMPLETED."""

    def __init__(self, backend_client: BackendClient, worker_id: str) -> None:
        self._backend_client = backend_client
        self._worker_id = worker_id

    async def run(self, state: PipelineState) -> PipelineState:
        state.job = await self._backend_client.update_job_status(
            state.job_id, status="COMPLETED", progress=100.0, worker_id=self._worker_id
        )
        return state
