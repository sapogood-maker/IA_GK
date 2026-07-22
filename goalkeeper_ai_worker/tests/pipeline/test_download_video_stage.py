"""Testes de DownloadVideoStage - HTTP mockado (backend + R2 fake, mesmo transport)."""
from __future__ import annotations

from pathlib import Path

import httpx

from worker.config.settings import get_settings
from worker.infrastructure.backend_client.client import BackendClient
from worker.pipeline.stages.download_video import DownloadVideoStage


async def test_downloads_the_video_to_the_workspace(base_state, tmp_path: Path) -> None:
    base_state.workspace_dir = tmp_path

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fake-r2.test":
            return httpx.Response(200, content=b"conteudo-fake-do-video")
        return httpx.Response(200, json={"url": "https://fake-r2.test/video.bin", "expires_in_seconds": 60})

    transport = httpx.MockTransport(handler)
    backend_client = BackendClient(get_settings(), transport=transport)
    stage = DownloadVideoStage(backend_client, transport=transport)

    result = await stage.run(base_state)

    assert result.download_path == tmp_path / "input_video"
    assert result.download_path.read_bytes() == b"conteudo-fake-do-video"

    await backend_client.aclose()
