import os
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.r2 import R2Service
from app.core.config import get_settings
from app.repositories.repositories import VideoRepository, ProcessingJobRepository, TrainingSessionRepository
from app.models.models import UploadStatus, ProcessingJobStatus

logger = logging.getLogger(__name__)


class VideoUploadService:
    """Service for handling video uploads to R2."""
    
    def __init__(self, db: AsyncSession, r2_service: R2Service):
        self.db = db
        self.r2_service = r2_service
        self.settings = get_settings()
        self.video_repo = VideoRepository(db)
        self.job_repo = ProcessingJobRepository(db)
        self.session_repo = TrainingSessionRepository(db)
    
    def _validate_file(self, file: UploadFile) -> tuple[bool, str | None]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file.filename:
            return False, "No filename provided"
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower().lstrip(".")
        if file_ext not in self.settings.allowed_video_extensions:
            return False, f"Invalid file extension. Allowed: {', '.join(self.settings.allowed_video_extensions)}"
        
        # Check MIME type
        if file.content_type and not file.content_type.startswith("video/"):
            return False, "Invalid MIME type. Must be a video file."
        
        return True, None
    
    async def _generate_r2_key(self, training_session_id: UUID, original_filename: str) -> str:
        """
        Generate R2 storage key based on structure: videos/goalkeeper_id/year/month/filename
        
        Retrieves the actual goalkeeper_id from the training session.
        """
        timestamp = datetime.utcnow()
        year = timestamp.year
        month = f"{timestamp.month:02d}"
        
        # Load training session from database to get actual goalkeeper_id
        session = await self.session_repo.get_by_id(training_session_id)
        if not session:
            raise ValueError(f"Training session {training_session_id} not found")
        
        goalkeeper_id = str(session.goalkeeper_id)
        
        # Generate unique filename
        file_ext = Path(original_filename).suffix.lower()
        base_name = Path(original_filename).stem
        unique_name = f"{base_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}{file_ext}"
        
        return f"videos/{goalkeeper_id}/{year}/{month}/{unique_name}"
    
    async def upload_video(
        self,
        training_session_id: UUID,
        file: UploadFile,
        temp_dir: str = "/tmp"
    ) -> dict:
        """
        Upload video to R2 and create database records.
        
        Returns:
            Dict with video_id, job_id, status, r2_key, r2_url
        """
        # Validate input
        is_valid, error = self._validate_file(file)
        if not is_valid:
            return {"error": error, "success": False}
        
        # Verify training session exists
        session = await self.session_repo.get_by_id(training_session_id)
        if not session:
            return {"error": "Training session not found", "success": False}
        
        try:
            # Save file temporarily
            temp_path = os.path.join(temp_dir, file.filename)
            os.makedirs(temp_dir, exist_ok=True)
            
            contents = await file.read()
            with open(temp_path, "wb") as f:
                f.write(contents)
            
            file_size = len(contents)
            
            # Check file size
            if file_size > self.settings.max_video_size_bytes:
                os.remove(temp_path)
                return {
                    "error": f"File too large. Max size: {self.settings.max_video_size_bytes / (1024*1024):.0f} MB",
                    "success": False
                }
            
            # Generate R2 key and upload
            r2_key = await self._generate_r2_key(training_session_id, file.filename)
            
            upload_success = await self.r2_service.upload_file(
                temp_path,
                r2_key,
                content_type=file.content_type or "video/mp4"
            )
            
            if not upload_success:
                os.remove(temp_path)
                return {"error": "Failed to upload to R2", "success": False}
            
            # Create Video record
            video = await self.video_repo.create(
                training_session_id=training_session_id,
                filename=Path(r2_key).name,
                original_filename=file.filename,
                mime_type=file.content_type or "video/mp4",
                file_size_bytes=file_size,
                r2_bucket=self.settings.r2_bucket_name,
                r2_key=r2_key,
                r2_url=self.r2_service.get_public_url(r2_key),
                upload_status=UploadStatus.UPLOADED.value
            )
            
            # Create ProcessingJob record
            job = await self.job_repo.create(
                video_id=video.id,
                job_type="video_processing",
                status=ProcessingJobStatus.PENDING.value,
                progress=0.0
            )
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            logger.info(f"Successfully uploaded video {video.id} to R2: {r2_key}")
            
            return {
                "success": True,
                "video_id": video.id,
                "job_id": job.id,
                "status": video.upload_status,
                "r2_key": r2_key,
                "r2_url": video.r2_url
            }
            
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return {"error": f"Unexpected error: {str(e)}", "success": False}
    
    async def get_video_status(self, video_id: UUID) -> dict:
        """Get video and its processing job status."""
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            return {"error": "Video not found", "success": False}
        
        jobs = await self.job_repo.get_by_video_id(video_id)
        latest_job = jobs[0] if jobs else None
        
        return {
            "success": True,
            "video_id": video_id,
            "video_status": video.upload_status,
            "job_status": latest_job.status if latest_job else None,
            "progress": latest_job.progress if latest_job else 0,
            "r2_url": video.r2_url
        }
    
    async def get_job_status(self, job_id: UUID) -> dict:
        """Get detailed processing job status."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            return {"error": "Job not found", "success": False}
        
        return {
            "success": True,
            "job_id": job_id,
            "video_id": job.video_id,
            "status": job.status,
            "progress": job.progress,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message
        }


async def get_video_upload_service(db: AsyncSession, r2_service: R2Service) -> VideoUploadService:
    """Dependency injection for VideoUploadService."""
    return VideoUploadService(db, r2_service)
