"""ReleaseLockStage: libera o Lock do video - roda mesmo apos falha (finally)."""
from __future__ import annotations

from worker.infrastructure.redis import lock
from worker.state.pipeline_state import PipelineState


class ReleaseLockStage:
    """Unica responsabilidade: liberar o Lock, se ele chegou a ser adquirido."""

    def __init__(self, redis_client, owner_id: str) -> None:
        self._redis_client = redis_client
        self._owner_id = owner_id

    async def run(self, state: PipelineState) -> PipelineState:
        if state.lock_acquired:
            await lock.release(self._redis_client, state.video_id, self._owner_id)
        return state
