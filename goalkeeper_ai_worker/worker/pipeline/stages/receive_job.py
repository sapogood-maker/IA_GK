"""ReceiveJobStage: busca os detalhes do Job na Worker API do backend."""
from __future__ import annotations

from worker.events.events import JobStarted, emit
from worker.infrastructure.backend_client.client import BackendClient
from worker.state.pipeline_state import PipelineState


class ReceiveJobStage:
    """Unica responsabilidade: obter os detalhes do Job via BackendClient."""

    def __init__(self, backend_client: BackendClient) -> None:
        self._backend_client = backend_client

    async def run(self, state: PipelineState) -> PipelineState:
        emit(JobStarted(job_id=state.job_id, video_id=state.video_id))
        state.job = await self._backend_client.get_job(state.job_id)
        return state
