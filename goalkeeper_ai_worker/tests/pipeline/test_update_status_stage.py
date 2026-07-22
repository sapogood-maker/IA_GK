"""Testes de UpdateStatusStage - HTTP mockado (httpx.MockTransport)."""
from __future__ import annotations

import json

import httpx

from worker.config.settings import get_settings
from worker.infrastructure.backend_client.client import BackendClient
from worker.pipeline.stages.update_status import UpdateStatusStage


async def test_marks_the_job_as_completed(base_state) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "id": "job-1", "video_id": "video-1", "status": "COMPLETED",
            "progress": 100.0, "error_message": None, "worker_id": "worker-test-01",
            "started_at": None, "completed_at": None,
        })

    backend_client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    stage = UpdateStatusStage(backend_client, worker_id="worker-test-01")

    result = await stage.run(base_state)

    assert captured["body"]["status"] == "COMPLETED"
    assert captured["body"]["progress"] == 100.0
    assert captured["body"]["worker_id"] == "worker-test-01"
    assert result.job.status == "COMPLETED"

    await backend_client.aclose()
