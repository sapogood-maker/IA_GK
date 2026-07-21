from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import (
    ProcessingJobCreate, ProcessingJobResponse, ProcessingJobUpdate,
    ProcessingJobStatusResponse
)
from app.repositories.repositories import ProcessingJobRepository, VideoRepository
from app.core.security import get_current_user
from app.core.authorization import is_admin, effective_club_scope, resolve_club_id_for_video, resolve_club_id_for_processing_job, COMMON_ERROR_RESPONSES
from app.models.models import User

router = APIRouter(
    prefix="/api/v1/processing-jobs",
    tags=["processing-jobs"],
    dependencies=[Depends(get_current_user)],
    responses=COMMON_ERROR_RESPONSES,
)


async def _ensure_job_access(job_id: UUID, current_user: User, db: AsyncSession) -> None:
    if is_admin(current_user):
        return
    club_id = await resolve_club_id_for_processing_job(db, job_id)
    if club_id != current_user.club_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=ProcessingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_processing_job(
    job_data: ProcessingJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new processing job."""
    video_repo = VideoRepository(db)

    # Validate video exists
    video = await video_repo.get_by_id(job_data.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if not is_admin(current_user):
        video_club_id = await resolve_club_id_for_video(db, job_data.video_id)
        if video_club_id != current_user.club_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job_repo = ProcessingJobRepository(db)
    return await job_repo.create(
        video_id=job_data.video_id,
        job_type=job_data.job_type,
        worker_id=job_data.worker_id,
        status=job_data.status,
        progress=job_data.progress,
        retry_count=job_data.retry_count,
        error_message=job_data.error_message
    )


@router.get("", response_model=list[ProcessingJobResponse])
async def list_processing_jobs(
    video_id: UUID = None,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List processing jobs with optional filtering."""
    job_repo = ProcessingJobRepository(db)
    scope = effective_club_scope(current_user)

    if scope is not None:
        return await job_repo.get_by_club_id(scope)
    if video_id:
        return await job_repo.get_by_video_id(video_id)
    elif status:
        return await job_repo.get_by_status(status)
    else:
        return await job_repo.get_all()


@router.get("/{job_id}/status", response_model=ProcessingJobStatusResponse)
async def get_processing_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed processing job status."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    await _ensure_job_access(job_id, current_user, db)

    return ProcessingJobStatusResponse(
        job_id=job.id,
        video_id=job.video_id,
        status=job.status,
        progress=job.progress,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific processing job."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    await _ensure_job_access(job_id, current_user, db)
    return job


@router.put("/{job_id}", response_model=ProcessingJobResponse)
async def update_processing_job(
    job_id: UUID,
    job_data: ProcessingJobUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a processing job."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    await _ensure_job_access(job_id, current_user, db)

    update_data = job_data.model_dump(exclude_unset=True)
    return await job_repo.update(job_id, **update_data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_processing_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a processing job."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    await _ensure_job_access(job_id, current_user, db)
    success = await job_repo.delete(job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")

