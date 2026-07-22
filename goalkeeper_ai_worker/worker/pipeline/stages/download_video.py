"""DownloadVideoStage: baixa o video original via URL assinada (R2)."""
from __future__ import annotations

import httpx

from worker.events.events import VideoDownloaded, emit
from worker.infrastructure.backend_client.client import BackendClient
from worker.infrastructure.storage import r2_client
from worker.state.pipeline_state import PipelineState


class DownloadVideoStage:
    """Unica responsabilidade: baixar o video para o workspace local."""

    def __init__(self, backend_client: BackendClient, transport: httpx.BaseTransport | None = None) -> None:
        self._backend_client = backend_client
        self._transport = transport

    async def run(self, state: PipelineState) -> PipelineState:
        presigned = await self._backend_client.get_download_url(state.job_id)
        download_path = state.workspace_dir / "input_video"
        await r2_client.download_to_path(presigned.url, download_path, transport=self._transport)
        state.download_path = download_path
        emit(VideoDownloaded(job_id=state.job_id, video_id=state.video_id, download_path=str(download_path)))
        return state
