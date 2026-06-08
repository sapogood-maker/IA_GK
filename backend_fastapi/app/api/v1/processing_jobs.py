from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import (
    ProcessingJobCreate, ProcessingJobResponse, ProcessingJobUpdate,
    ProcessingJobStatusResponse
)
from app.repositories.repositories import ProcessingJobRepository, VideoRepository

router = APIRouter(prefix="/api/v1/processing-jobs", tags=["processing-jobs"])


@router.post("", response_model=ProcessingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_processing_job(job_data: ProcessingJobCreate, db: AsyncSession = Depends(get_db)):
    """Create a new processing job."""
    video_repo = VideoRepository(db)
    
    # Validate video exists
    video = await video_repo.get_by_id(job_data.video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
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
    db: AsyncSession = Depends(get_db)
):
    """List processing jobs with optional filtering."""
    job_repo = ProcessingJobRepository(db)
    
    if video_id:
        return await job_repo.get_by_video_id(video_id)
    elif status:
        return await job_repo.get_by_status(status)
    else:
        return await job_repo.get_all()


@router.get("/{job_id}/status", response_model=ProcessingJobStatusResponse)
async def get_processing_job_status(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get detailed processing job status."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    
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
async def get_processing_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific processing job."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    return job


@router.put("/{job_id}", response_model=ProcessingJobResponse)
async def update_processing_job(
    job_id: UUID,
    job_data: ProcessingJobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a processing job."""
    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
    
    update_data = job_data.model_dump(exclude_unset=True)
    return await job_repo.update(job_id, **update_data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_processing_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a processing job."""
    job_repo = ProcessingJobRepository(db)
    success = await job_repo.delete(job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")

