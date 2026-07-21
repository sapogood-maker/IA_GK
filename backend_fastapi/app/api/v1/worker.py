"""Endpoints exclusivos do futuro AI Worker.

Autenticacao: API Key (X-Worker-Api-Key), nunca JWT de usuario - ver
app/core/worker_auth.py e AI_WORKER_ARCHITECTURE.md secao 6. Nenhum
endpoint humano (routers em users.py, clubs.py etc.) aceita essa API Key,
e nenhum endpoint deste arquivo aceita o JWT humano - os dois mecanismos
de autenticacao sao completamente separados.

Ainda SEM processamento real: nenhum destes endpoints roda inferencia,
tracking ou qualquer visao computacional - so entregam a infraestrutura
(detalhes do job, atualizacao de status, URLs assinadas do R2) que o
futuro Worker vai consumir (ver SPRINT7_REPORT.md).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timezone

from app.db.base import get_db
from app.core.config import get_settings
from app.core.r2 import get_r2_service, R2Service
from app.core.worker_auth import require_worker_api_key
from app.core.authorization import require_roles
from app.core.queue import get_queue_health
from app.models.models import UserRole, ProcessingJobStatus
from app.repositories.repositories import ProcessingJobRepository, VideoRepository
from app.schemas.schemas import (
    ProcessingJobResponse,
    WorkerJobStatusUpdate,
    PresignedUrlResponse,
    ArtifactUploadUrlRequest,
    ArtifactUploadUrlResponse,
    QueueHealthResponse,
)

# --- Router do Worker (API Key, nunca JWT) ---
router = APIRouter(
    prefix="/api/v1/worker",
    tags=["worker"],
    dependencies=[Depends(require_worker_api_key)],
)

# --- Router de diagnostico para humanos (JWT/SYSTEM_ADMIN, nunca API Key) ---
# Fica neste arquivo por tratar do mesmo subsistema (fila), mas e um objeto
# de router totalmente separado - dependencies de um nao vazam para o outro.
admin_router = APIRouter(
    prefix="/api/v1/queue",
    tags=["queue"],
    dependencies=[Depends(require_roles(UserRole.SYSTEM_ADMIN))],
)


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
async def get_job_details(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """O Worker consulta os detalhes de um job (video_id, status atual,
    tentativas, etc.) apos recebe-lo da fila."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    return job


@router.put("/jobs/{job_id}/status", response_model=ProcessingJobResponse)
async def update_job_status(job_id: UUID, update: WorkerJobStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Reporta progresso, conclusao (status=COMPLETED) ou falha
    (status=FAILED + error_message) de um job. Consolidado num unico
    endpoint em vez de 3 separados (progresso/concluir/falhar) - evita
    duplicar validacao/logica quase identica."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")

    update_data = {
        "status": update.status,
        "progress": update.progress,
        "error_message": update.error_message,
        "worker_id": update.worker_id,
    }

    # Marca started_at/completed_at automaticamente nas transicoes
    # relevantes, para o Worker nao precisar gerenciar esses timestamps.
    now = datetime.now(timezone.utc)
    if update.status not in (ProcessingJobStatus.QUEUED.value,) and job.started_at is None:
        update_data["started_at"] = now
    if update.status in (
        ProcessingJobStatus.COMPLETED.value,
        ProcessingJobStatus.FAILED.value,
        ProcessingJobStatus.CANCELLED.value,
    ):
        update_data["completed_at"] = now

    updated = await job_repo.update(job_id, **update_data)
    return updated


@router.post("/jobs/{job_id}/download-url", response_model=PresignedUrlResponse)
async def get_video_download_url(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    r2_service: R2Service = Depends(get_r2_service),
):
    """URL assinada e temporaria para o Worker baixar o video original do
    job - nunca recebe as credenciais mestras do R2 (ver
    AI_WORKER_ARCHITECTURE.md secao 11)."""
    job_repo = ProcessingJobRepository(db)
    video_repo = VideoRepository(db)

    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")

    video = await video_repo.get_by_id(job.video_id)
    if not video or not video.r2_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found")

    settings = get_settings()
    url = await r2_service.generate_presigned_url(
        video.r2_key, expiration_seconds=settings.worker_download_url_expiration_seconds
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate download URL - check R2 configuration",
        )

    return PresignedUrlResponse(
        url=url, expires_in_seconds=settings.worker_download_url_expiration_seconds
    )


@router.post("/jobs/{job_id}/artifacts/upload-url", response_model=ArtifactUploadUrlResponse)
async def get_artifact_upload_url(
    job_id: UUID,
    upload_request: ArtifactUploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    r2_service: R2Service = Depends(get_r2_service),
):
    """URL assinada e temporaria para o Worker subir um artefato (thumbnail,
    clipe, heatmap, lote de predicoes) gerado durante o processamento -
    nunca recebe as credenciais mestras do R2."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")

    r2_key = f"artifacts/{job.video_id}/{job_id}/{upload_request.filename}"

    settings = get_settings()
    url = await r2_service.generate_presigned_upload_url(
        r2_key,
        expiration_seconds=settings.worker_upload_url_expiration_seconds,
        content_type=upload_request.content_type,
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate upload URL - check R2 configuration",
        )

    return ArtifactUploadUrlResponse(
        url=url, r2_key=r2_key, expires_in_seconds=settings.worker_upload_url_expiration_seconds
    )


@admin_router.get("/health", response_model=QueueHealthResponse)
async def queue_health():
    """Diagnostico simples da fila Redis para humanos (SYSTEM_ADMIN) -
    quantidade de mensagens ainda no stream e conectividade. Sem
    Prometheus (fora do escopo desta sprint)."""
    health = await get_queue_health()
    return QueueHealthResponse(**health)
