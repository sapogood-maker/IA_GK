"""AcquireLockStage: adquire o Lock distribuido por video (ADR-001/003)."""
from __future__ import annotations

from worker.core.exceptions import PipelineError
from worker.infrastructure.redis import lock
from worker.state.pipeline_state import PipelineState


class AcquireLockStage:
    """Unica responsabilidade: adquirir o Lock exclusivo do video."""

    def __init__(self, redis_client, owner_id: str, ttl_seconds: int) -> None:
        self._redis_client = redis_client
        self._owner_id = owner_id
        self._ttl_seconds = ttl_seconds

    async def run(self, state: PipelineState) -> PipelineState:
        acquired = await lock.acquire(self._redis_client, state.video_id, self._owner_id, self._ttl_seconds)
        if not acquired:
            raise PipelineError(f"Lock do video {state.video_id} ja esta em uso por outro Worker")
        state.lock_acquired = True
        return state
