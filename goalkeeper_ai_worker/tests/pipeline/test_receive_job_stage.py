"""Testes de ReceiveJobStage - HTTP mockado (httpx.MockTransport)."""
from __future__ import annotations

import httpx

from worker.config.settings import get_settings
from worker.infrastructure.backend_client.client import BackendClient
from worker.pipeline.stages.receive_job import ReceiveJobStage


async def test_populates_state_job_from_the_backend(base_state) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": "job-1", "video_id": "video-1", "status": "QUEUED",
            "progress": 0.0, "error_message": None, "worker_id": None,
            "started_at": None, "completed_at": None,
        })

    backend_client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    stage = ReceiveJobStage(backend_client)

    result = await stage.run(base_state)

    assert result.job is not None
    assert result.job.id == "job-1"
    assert result.job.status == "QUEUED"

    await backend_client.aclose()
