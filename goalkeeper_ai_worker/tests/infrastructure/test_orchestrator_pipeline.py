"""Teste de integracao do Pipeline completo: Lock real (Redis), Backend API e
R2 mockados (httpx.MockTransport compartilhado) - sem depender de um backend
real rodando. A validacao contra o backend real acontece na verificacao
manual da Sprint W3 (ver SPRINT_W3_REPORT.md)."""
from __future__ import annotations

import json

import httpx

from worker.config.settings import get_settings
from worker.contracts.queue_message import JobMessage
from worker.infrastructure.backend_client.client import BackendClient
from worker.infrastructure.redis import lock
from worker.orchestrator.orchestrator import WorkerOrchestrator

JOB_ID = "job-int-1"
VIDEO_ID = "video-int-1"


def _make_happy_path_handler(video_bytes: bytes):
    state = {"status": "QUEUED", "uploaded_json": None}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if request.url.host == "fake-r2.test":
            if request.method == "GET":
                return httpx.Response(200, content=video_bytes)
            state["uploaded_json"] = request.content
            return httpx.Response(200)

        if path == f"/api/v1/worker/jobs/{JOB_ID}" and request.method == "GET":
            return httpx.Response(200, json={
                "id": JOB_ID, "video_id": VIDEO_ID, "status": state["status"],
                "progress": 0.0, "error_message": None, "worker_id": None,
                "started_at": None, "completed_at": None,
            })
        if path == f"/api/v1/worker/jobs/{JOB_ID}/status" and request.method == "PUT":
            body = json.loads(request.content)
            state["status"] = body["status"]
            return httpx.Response(200, json={
                "id": JOB_ID, "video_id": VIDEO_ID, "status": body["status"],
                "progress": body.get("progress"), "error_message": body.get("error_message"),
                "worker_id": body.get("worker_id"), "started_at": None, "completed_at": None,
            })
        if path == f"/api/v1/worker/jobs/{JOB_ID}/download-url" and request.method == "POST":
            return httpx.Response(200, json={"url": "https://fake-r2.test/video.bin", "expires_in_seconds": 60})
        if path == f"/api/v1/worker/jobs/{JOB_ID}/artifacts/upload-url" and request.method == "POST":
            return httpx.Response(200, json={
                "url": "https://fake-r2.test/artifact.json",
                "r2_key": f"artifacts/{VIDEO_ID}/{JOB_ID}/artifact.json",
                "expires_in_seconds": 60,
            })
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    return handler, state


async def test_full_pipeline_completes_successfully(redis_client, real_video_path) -> None:
    settings = get_settings()
    handler, state = _make_happy_path_handler(real_video_path.read_bytes())
    transport = httpx.MockTransport(handler)
    backend_client = BackendClient(settings, transport=transport)
    orchestrator = WorkerOrchestrator(settings, redis_client, backend_client, transport=transport)

    message = JobMessage(message_id="0-1", job_id=JOB_ID, video_id=VIDEO_ID)
    result = await orchestrator.process_job(message)

    assert result.status == "COMPLETED"
    assert result.errors == []
    assert not result.workspace_dir.exists()
    assert state["status"] == "COMPLETED"

    uploaded = json.loads(state["uploaded_json"])
    assert uploaded["status"] == "processed"
    assert uploaded["metadata"]["engine_name"] == "basic_vision"
    assert uploaded["frame_metadata"]["frame_count"] == 10
    assert uploaded["frames_processed"] == 10

    await backend_client.aclose()


async def test_pipeline_marks_job_failed_when_job_not_found(redis_client) -> None:
    settings = get_settings()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Processing job not found"})

    transport = httpx.MockTransport(handler)
    backend_client = BackendClient(settings, transport=transport)
    orchestrator = WorkerOrchestrator(settings, redis_client, backend_client, transport=transport)

    message = JobMessage(message_id="0-2", job_id="missing-job", video_id="video-x")
    result = await orchestrator.process_job(message)

    assert result.status == "FAILED"
    assert len(result.errors) == 1
    assert result.lock_acquired is False
    assert result.workspace_dir is None

    await backend_client.aclose()


async def test_pipeline_fails_gracefully_when_lock_already_held(redis_client, real_video_path) -> None:
    settings = get_settings()
    handler, _ = _make_happy_path_handler(real_video_path.read_bytes())
    transport = httpx.MockTransport(handler)
    backend_client = BackendClient(settings, transport=transport)

    await lock.acquire(redis_client, VIDEO_ID, "outro-worker", ttl_seconds=60)

    orchestrator = WorkerOrchestrator(settings, redis_client, backend_client, transport=transport)
    message = JobMessage(message_id="0-3", job_id=JOB_ID, video_id=VIDEO_ID)
    result = await orchestrator.process_job(message)

    assert result.status == "FAILED"
    assert result.lock_acquired is False

    await lock.release(redis_client, VIDEO_ID, "outro-worker")
    await backend_client.aclose()
