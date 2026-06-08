from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.core.r2 import get_r2_service, R2Service
from app.schemas.schemas import (
    VideoCreate, VideoResponse, VideoUpdate,
    VideoUploadResponse, VideoStatusResponse,
    ProcessingJobStatusResponse
)
from app.repositories.repositories import VideoRepository, TrainingSessionRepository, ProcessingJobRepository
from app.services.video_upload_service import VideoUploadService

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    training_session_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    r2_service: R2Service = Depends(get_r2_service)
):
    """
    Upload a video file to R2.
    
    Accepts multipart file upload with validation for:
    - File extensions: mp4, mov, avi, mkv
    - MIME type: video/*
    - Maximum file size (configurable via ENV)
    
    Returns:
    - video_id: UUID of created video
    - job_id: UUID of created processing job
    - status: Upload status (UPLOADED)
    - r2_key: Path in R2 bucket
    - r2_url: Public URL to video
    """
    upload_service = VideoUploadService(db, r2_service)
    result = await upload_service.upload_video(training_session_id, file)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Unknown error")
        )
    
    return VideoUploadResponse(
        video_id=result["video_id"],
        job_id=result["job_id"],
        status=result["status"],
        r2_key=result["r2_key"],
        r2_url=result["r2_url"]
    )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    r2_service: R2Service = Depends(get_r2_service)
):
    """
    Get video and processing job status.
    
    Returns:
    - video_id: UUID of video
    - video_status: Current upload/processing status
    - job_status: Current processing job status
    - progress: Processing progress (0-100)
    - r2_url: Public URL to video
    """
    upload_service = VideoUploadService(db, r2_service)
    result = await upload_service.get_video_status(video_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Video not found")
        )
    
    return VideoStatusResponse(
        video_id=result["video_id"],
        video_status=result["video_status"],
        job_status=result["job_status"],
        progress=result["progress"],
        r2_url=result["r2_url"]
    )


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(video_data: VideoCreate, db: AsyncSession = Depends(get_db)):
    """Create a new video record (legacy endpoint)."""
    session_repo = TrainingSessionRepository(db)
    
    # Validate training session exists
    session = await session_repo.get_by_id(video_data.training_session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
    
    video_repo = VideoRepository(db)
    return await video_repo.create(
        training_session_id=video_data.training_session_id,
        filename=video_data.filename,
        original_filename=video_data.original_filename,
        mime_type=video_data.mime_type,
        file_size_bytes=video_data.file_size_bytes,
        duration_seconds=video_data.duration_seconds,
        r2_bucket=video_data.r2_bucket,
        r2_key=video_data.r2_key,
        r2_url=video_data.r2_url,
        upload_status=video_data.upload_status
    )


@router.get("", response_model=list[VideoResponse])
async def list_videos(
    training_session_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """List videos with optional filtering by training session."""
    video_repo = VideoRepository(db)
    
    if training_session_id:
        return await video_repo.get_by_training_session_id(training_session_id)
    else:
        return await video_repo.get_all()


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific video."""
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: UUID,
    video_data: VideoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a video."""
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    update_data = video_data.model_dump(exclude_unset=True)
    return await video_repo.update(video_id, **update_data)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(video_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a video."""
    video_repo = VideoRepository(db)
    success = await video_repo.delete(video_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

