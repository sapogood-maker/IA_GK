"""Testes de worker.infrastructure.backend_client - HTTP mockado (httpx.MockTransport),
sem depender de um backend real rodando. A validacao contra o backend real
acontece na verificacao manual de ponta a ponta da Sprint W2."""
from __future__ import annotations

import json

import httpx
import pytest

from worker.config.settings import get_settings
from worker.core.exceptions import BackendRequestError, BackendUnavailableError
from worker.infrastructure.backend_client.client import BackendClient

JOB_RESPONSE = {
    "id": "job-1",
    "video_id": "video-1",
    "status": "QUEUED",
    "progress": 0.0,
    "error_message": None,
    "worker_id": None,
    "started_at": None,
    "completed_at": None,
}


async def test_get_job_sends_auth_and_version_headers_and_parses_response() -> None:
    """A camada HTTP generica deve injetar X-Worker-Api-Key e X-Worker-Version
    em toda chamada, e get_job deve usar GET no path correto."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["headers"] = request.headers
        return httpx.Response(200, json=JOB_RESPONSE)

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    job = await client.get_job("job-1")
    await client.aclose()

    assert captured["method"] == "GET"
    assert captured["path"] == "/api/v1/worker/jobs/job-1"
    assert captured["headers"]["x-worker-api-key"] == "test-api-key"
    assert captured["headers"]["x-worker-version"] == "1.0"
    assert job.id == "job-1"
    assert job.status == "QUEUED"


async def test_get_job_not_found_raises_backend_request_error() -> None:
    """Status >= 400 deve virar BackendRequestError com o status_code correto."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Processing job not found"})

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(BackendRequestError) as exc_info:
        await client.get_job("does-not-exist")
    await client.aclose()

    assert exc_info.value.status_code == 404


async def test_update_job_status_sends_correct_body() -> None:
    """update_job_status deve usar PUT e enviar exatamente os campos do contrato."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["json"] = json.loads(request.content) if request.content else None
        return httpx.Response(200, json={**JOB_RESPONSE, "status": "DOWNLOADING", "progress": 5.0})

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    job = await client.update_job_status("job-1", status="DOWNLOADING", progress=5.0, worker_id="worker-01")
    await client.aclose()

    assert captured["method"] == "PUT"
    assert captured["path"] == "/api/v1/worker/jobs/job-1/status"
    assert captured["json"] == {
        "status": "DOWNLOADING",
        "progress": 5.0,
        "error_message": None,
        "worker_id": "worker-01",
    }
    assert job.status == "DOWNLOADING"
    assert job.progress == 5.0


async def test_get_download_url_returns_presigned_url() -> None:
    """get_download_url deve usar POST no path correto e devolver a URL assinada."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/worker/jobs/job-1/download-url"
        return httpx.Response(200, json={"url": "https://r2.example.com/video.mp4", "expires_in_seconds": 3600})

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    presigned = await client.get_download_url("job-1")
    await client.aclose()

    assert presigned.url == "https://r2.example.com/video.mp4"
    assert presigned.expires_in_seconds == 3600


async def test_get_artifact_upload_url_sends_filename_and_content_type() -> None:
    """get_artifact_upload_url deve enviar filename/content_type e devolver r2_key."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "url": "https://r2.example.com/artifacts/video-1/job-1/thumb.jpg",
                "r2_key": "artifacts/video-1/job-1/thumb.jpg",
                "expires_in_seconds": 3600,
            },
        )

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))
    upload_url = await client.get_artifact_upload_url("job-1", "thumb.jpg", content_type="image/jpeg")
    await client.aclose()

    assert captured["json"] == {"filename": "thumb.jpg", "content_type": "image/jpeg"}
    assert upload_url.r2_key == "artifacts/video-1/job-1/thumb.jpg"


async def test_network_failure_raises_backend_unavailable_error() -> None:
    """Uma falha de rede/conexao deve virar BackendUnavailableError, nao propagar httpx.HTTPError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = BackendClient(get_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(BackendUnavailableError):
        await client.get_job("job-1")
    await client.aclose()
