"""Testes de UploadArtifactStage - HTTP mockado (backend + R2 fake, mesmo transport)."""
from __future__ import annotations

from pathlib import Path

import httpx

from worker.config.settings import get_settings
from worker.infrastructure.backend_client.client import BackendClient
from worker.pipeline.stages.upload_artifact import UploadArtifactStage


async def test_uploads_the_artifact_and_returns_its_r2_key(base_state, tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text('{"status": "processed"}', encoding="utf-8")
    base_state.artifact_path = artifact_path

    uploaded: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fake-r2.test":
            uploaded["content"] = request.content
            return httpx.Response(200)
        return httpx.Response(200, json={
            "url": "https://fake-r2.test/artifact.json",
            "r2_key": "artifacts/video-1/job-1/artifact.json",
            "expires_in_seconds": 60,
        })

    transport = httpx.MockTransport(handler)
    backend_client = BackendClient(get_settings(), transport=transport)
    stage = UploadArtifactStage(backend_client, transport=transport)

    await stage.run(base_state)

    assert uploaded["content"] == artifact_path.read_bytes()

    await backend_client.aclose()
