"""Interface comum de todo Stage do Pipeline."""
from __future__ import annotations

from typing import Protocol

from worker.state.pipeline_state import PipelineState


class Stage(Protocol):
    """Todo Stage recebe e devolve o mesmo PipelineState - nunca dezenas de
    parametros soltos."""

    async def run(self, state: PipelineState) -> PipelineState: ...
