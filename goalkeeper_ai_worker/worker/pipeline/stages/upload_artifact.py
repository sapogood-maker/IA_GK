"""UploadArtifactStage: envia o artefato gerado via URL assinada (R2)."""
from __future__ import annotations

import httpx

from worker.events.events import UploadFinished, emit
from worker.infrastructure.backend_client.client import BackendClient
from worker.infrastructure.storage import r2_client
from worker.state.pipeline_state import PipelineState


class UploadArtifactStage:
    """Unica responsabilidade: subir o artefato gerado para o R2."""

    def __init__(self, backend_client: BackendClient, transport: httpx.BaseTransport | None = None) -> None:
        self._backend_client = backend_client
        self._transport = transport

    async def run(self, state: PipelineState) -> PipelineState:
        upload_url = await self._backend_client.get_artifact_upload_url(
            state.job_id, filename="artifact.json", content_type="application/json"
        )
        await r2_client.upload_file(
            upload_url.url, state.artifact_path, content_type="application/json", transport=self._transport
        )
        emit(UploadFinished(job_id=state.job_id, video_id=state.video_id, r2_key=upload_url.r2_key))
        return state
