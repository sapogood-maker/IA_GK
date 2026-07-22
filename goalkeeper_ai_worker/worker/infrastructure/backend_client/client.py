"""Cliente da Worker API do backend.

Estrutura em duas camadas deliberadamente:

- `_BaseBackendClient`: a camada HTTP generica (`_request`) - injeta
  autenticacao/identificacao de protocolo, trata erro de rede e de status,
  e nao conhece nenhum endpoint especifico.
- `BackendClient`: hoje concentra todos os metodos de endpoint. Quando o
  numero de endpoints crescer, `get_job`/`update_job_status` podem migrar
  para um `jobs.py` e `get_download_url`/`get_artifact_upload_url` para um
  `storage.py`, cada um como um mixin de `_BaseBackendClient` - sem tocar
  em `_request`. Nenhum desses arquivos e criado nesta sprint; so a
  estrutura que permite a divisao sem refatoracao.
"""
from __future__ import annotations

from typing import Any

import httpx

from worker.config.settings import WorkerSettings
from worker.contracts.backend_api import (
    ArtifactUploadUrl,
    ArtifactUploadUrlRequest,
    JobDetails,
    JobStatusUpdate,
    PresignedUrl,
)
from worker.core.exceptions import BackendRequestError, BackendUnavailableError


class _BaseBackendClient:
    """Camada HTTP generica: autenticacao, identificacao de protocolo e
    tratamento de erro, comuns a qualquer endpoint da Worker API."""

    def __init__(self, settings: WorkerSettings, transport: httpx.BaseTransport | None = None) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.backend_api_url,
            headers={
                "X-Worker-Api-Key": settings.api_key,
                "X-Worker-Version": settings.protocol_version,
            },
            timeout=30.0,
            transport=transport,
        )

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa uma chamada HTTP e devolve o corpo JSON da resposta.

        Erros de rede/timeout viram BackendUnavailableError; respostas com
        status >= 400 viram BackendRequestError."""
        try:
            response = await self._http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(f"Falha ao contatar {path}: {exc}") from exc

        if response.status_code >= 400:
            raise BackendRequestError(response.status_code, response.text)

        return response.json()

    async def aclose(self) -> None:
        """Fecha o cliente HTTP subjacente."""
        await self._http.aclose()

    async def __aenter__(self) -> "_BaseBackendClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.aclose()


class BackendClient(_BaseBackendClient):
    """Fachada com os endpoints da Worker API usados pelo Worker."""

    async def get_job(self, job_id: str) -> JobDetails:
        """GET /api/v1/worker/jobs/{job_id}."""
        body = await self._request("GET", f"/api/v1/worker/jobs/{job_id}")
        return JobDetails.model_validate(body)

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float | None = None,
        error_message: str | None = None,
        worker_id: str | None = None,
    ) -> JobDetails:
        """PUT /api/v1/worker/jobs/{job_id}/status."""
        update = JobStatusUpdate(
            status=status, progress=progress, error_message=error_message, worker_id=worker_id
        )
        body = await self._request(
            "PUT", f"/api/v1/worker/jobs/{job_id}/status", json=update.model_dump()
        )
        return JobDetails.model_validate(body)

    async def get_download_url(self, job_id: str) -> PresignedUrl:
        """POST /api/v1/worker/jobs/{job_id}/download-url."""
        body = await self._request("POST", f"/api/v1/worker/jobs/{job_id}/download-url")
        return PresignedUrl.model_validate(body)

    async def get_artifact_upload_url(
        self, job_id: str, filename: str, content_type: str = "application/octet-stream"
    ) -> ArtifactUploadUrl:
        """POST /api/v1/worker/jobs/{job_id}/artifacts/upload-url."""
        request = ArtifactUploadUrlRequest(filename=filename, content_type=content_type)
        body = await self._request(
            "POST",
            f"/api/v1/worker/jobs/{job_id}/artifacts/upload-url",
            json=request.model_dump(),
        )
        return ArtifactUploadUrl.model_validate(body)
