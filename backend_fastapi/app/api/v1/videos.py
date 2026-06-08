from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.base import get_db
from app.schemas.schemas import VideoCreate, VideoResponse, VideoUpdate
from app.repositories.repositories import VideoRepository, TrainingSessionRepository

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(video_data: VideoCreate, db: AsyncSession = Depends(get_db)):
    """Create a new video."""
    session_repo = TrainingSessionRepository(db)
    
    # Validate training session exists
    session = await session_repo.get_by_id(video_data.training_session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
    
    video_repo = VideoRepository(db)
    return await video_repo.create(
        training_session_id=video_data.training_session_id,
        filename=video_data.filename,
        r2_key=video_data.r2_key,
        duration_seconds=video_data.duration_seconds,
        size_bytes=video_data.size_bytes,
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
