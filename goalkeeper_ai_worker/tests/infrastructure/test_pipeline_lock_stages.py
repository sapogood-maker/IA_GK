"""Testes de AcquireLockStage/ReleaseLockStage - Redis real e descartavel."""
from __future__ import annotations

from datetime import datetime, timezone

from worker.core.exceptions import PipelineError
from worker.infrastructure.redis import lock
from worker.pipeline.stages.acquire_lock import AcquireLockStage
from worker.pipeline.stages.release_lock import ReleaseLockStage
from worker.state.pipeline_state import PipelineState

import pytest


def _make_state(video_id: str = "video-lock-1") -> PipelineState:
    return PipelineState(
        job_id="job-1", video_id=video_id, message_id="0-1", started_at=datetime.now(timezone.utc)
    )


async def test_acquire_lock_stage_marks_lock_acquired_on_success(redis_client) -> None:
    state = _make_state()
    stage = AcquireLockStage(redis_client, owner_id="worker-a", ttl_seconds=60)

    result = await stage.run(state)

    assert result.lock_acquired is True


async def test_acquire_lock_stage_raises_when_already_locked(redis_client) -> None:
    state = _make_state()
    await lock.acquire(redis_client, state.video_id, "outro-worker", ttl_seconds=60)

    stage = AcquireLockStage(redis_client, owner_id="worker-a", ttl_seconds=60)
    with pytest.raises(PipelineError):
        await stage.run(state)

    await lock.release(redis_client, state.video_id, "outro-worker")


async def test_release_lock_stage_releases_when_acquired(redis_client) -> None:
    state = _make_state()
    await AcquireLockStage(redis_client, owner_id="worker-a", ttl_seconds=60).run(state)

    await ReleaseLockStage(redis_client, owner_id="worker-a").run(state)

    reacquired = await lock.acquire(redis_client, state.video_id, "worker-b", ttl_seconds=60)
    assert reacquired is True
    await lock.release(redis_client, state.video_id, "worker-b")


async def test_release_lock_stage_is_a_noop_when_never_acquired(redis_client) -> None:
    state = _make_state()

    await ReleaseLockStage(redis_client, owner_id="worker-a").run(state)
