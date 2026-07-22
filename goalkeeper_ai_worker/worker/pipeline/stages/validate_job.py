"""ValidateJobStage: confirma que o Job retornado pelo backend e consistente
com a mensagem da fila e ainda esta em um estado consumivel."""
from __future__ import annotations

from worker.core.exceptions import PipelineError
from worker.state.pipeline_state import PipelineState

_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


class ValidateJobStage:
    """Unica responsabilidade: validar consistencia e estado do Job antes de prosseguir."""

    async def run(self, state: PipelineState) -> PipelineState:
        if state.job is None:
            raise PipelineError(f"Job {state.job_id} nao foi carregado antes da validacao")
        if state.job.video_id != state.video_id:
            raise PipelineError(
                f"video_id da mensagem ({state.video_id}) nao bate com o do Job ({state.job.video_id})"
            )
        if state.job.status in _TERMINAL_STATUSES:
            raise PipelineError(f"Job {state.job_id} ja esta em estado terminal: {state.job.status}")
        return state
