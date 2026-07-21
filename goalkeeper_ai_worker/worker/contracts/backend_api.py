"""Formato dos dados trocados com a Worker API do backend (REST).

Espelha os campos de `app/schemas/schemas.py` do backend
(`ProcessingJobResponse`, `WorkerJobStatusUpdate`, `PresignedUrlResponse`,
`ArtifactUploadUrlRequest`, `ArtifactUploadUrlResponse`), mas e definido de
forma completamente independente - nenhum import do backend.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobDetails(BaseModel):
    """Resposta de GET /api/v1/worker/jobs/{job_id}."""

    id: str
    video_id: str
    status: str
    progress: float | None = None
    error_message: str | None = None
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobStatusUpdate(BaseModel):
    """Corpo de PUT /api/v1/worker/jobs/{job_id}/status."""

    status: str
    progress: float | None = None
    error_message: str | None = None
    worker_id: str | None = None


class PresignedUrl(BaseModel):
    """Resposta de POST /api/v1/worker/jobs/{job_id}/download-url."""

    url: str
    expires_in_seconds: int


class ArtifactUploadUrlRequest(BaseModel):
    """Corpo de POST /api/v1/worker/jobs/{job_id}/artifacts/upload-url."""

    filename: str
    content_type: str = "application/octet-stream"


class ArtifactUploadUrl(BaseModel):
    """Resposta de POST /api/v1/worker/jobs/{job_id}/artifacts/upload-url."""

    url: str
    r2_key: str
    expires_in_seconds: int
