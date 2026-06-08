# Cloudflare R2 Integration - Quick Reference

## Key Files

### Core R2 Service
- `app/core/r2.py` - R2 client service with upload/delete/status methods
- `app/core/config.py` - Configuration for R2 credentials and settings

### Services
- `app/services/video_upload_service.py` - Orchestrates video upload workflow

### API Endpoints
- `app/api/v1/videos.py` - Video endpoints including upload
- `app/api/v1/processing_jobs.py` - Processing job endpoints including status

### Database
- `app/models/models.py` - Updated Video and ProcessingJob models
- `alembic/versions/003_add_r2_integration.py` - Migration for R2 fields

### Database Schema
- `app/schemas/schemas.py` - Updated schemas for new fields

## Upload Flow

```
1. Client submits video file
   ↓
2. Endpoint validates file (extension, size, MIME type)
   ↓
3. Save to temporary location
   ↓
4. Upload to R2 at: videos/{gk_id}/{year}/{month}/{filename}
   ↓
5. Create Video record with upload_status=UPLOADED
   ↓
6. Create ProcessingJob record with status=PENDING
   ↓
7. Return response with video_id, job_id, r2_key, r2_url
   ↓
8. Clean up temporary file
```

## API Quick Reference

### Upload Video

```bash
curl -X POST "http://localhost:8001/api/v1/videos/upload" \
  -F "file=@video.mp4" \
  -F "training_session_id=123e4567-e89b-12d3-a456-426614174000"
```

Response:
```json
{
  "video_id": "uuid",
  "job_id": "uuid",
  "status": "UPLOADED",
  "r2_key": "videos/12345678/2026/06/video_20260608_160000.mp4",
  "r2_url": "https://cdn.example.com/videos/12345678/2026/06/video_20260608_160000.mp4"
}
```

### Get Video Status

```bash
curl "http://localhost:8001/api/v1/videos/{video_id}/status"
```

Response:
```json
{
  "video_id": "uuid",
  "video_status": "PROCESSING",
  "job_status": "RUNNING",
  "progress": 45.5,
  "r2_url": "https://cdn.example.com/videos/..."
}
```

### Get Job Status

```bash
curl "http://localhost:8001/api/v1/processing-jobs/{job_id}/status"
```

Response:
```json
{
  "job_id": "uuid",
  "video_id": "uuid",
  "status": "RUNNING",
  "progress": 45.5,
  "started_at": "2026-06-08T16:00:00+00:00",
  "completed_at": null,
  "error_message": null
}
```

## Configuration Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create .env file with R2 credentials:**
   ```env
   R2_ACCOUNT_ID=your-account-id
   R2_ACCESS_KEY_ID=your-access-key-id
   R2_SECRET_ACCESS_KEY=your-secret-access-key
   R2_BUCKET_NAME=goalkeeper-ai-videos
   R2_PUBLIC_URL=https://videos.example.com
   MAX_VIDEO_SIZE_BYTES=524288000
   ```

3. **Run Migration:**
   ```bash
   alembic upgrade head
   ```

4. **Start Server:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Enum Values

### Upload Status
- `PENDING` - Waiting to upload
- `UPLOADED` - In R2
- `PROCESSING` - Being analyzed
- `COMPLETED` - Done
- `FAILED` - Error

### Job Status
- `PENDING` - Created, not started
- `RUNNING` - Actively processing
- `COMPLETED` - Finished
- `FAILED` - Error occurred

## Database Fields Added

### Video Table
- `original_filename` - User's original filename
- `mime_type` - Content type
- `file_size_bytes` - File size in bytes
- `r2_bucket` - Bucket name
- `r2_url` - Public URL
- `uploaded_at` - Upload completion time

### ProcessingJob Table
- `job_type` - Type of processing
- `worker_id` - Assigned worker
- `retry_count` - Number of retries

## Testing

### Manual Upload Test

```python
# Python script to test upload
import requests
from pathlib import Path

video_path = Path("test_video.mp4")
session_id = "123e4567-e89b-12d3-a456-426614174000"

with open(video_path, "rb") as f:
    files = {"file": (video_path.name, f, "video/mp4")}
    params = {"training_session_id": session_id}
    response = requests.post(
        "http://localhost:8001/api/v1/videos/upload",
        files=files,
        params=params
    )

print(response.json())
```

### Test Validation

1. File extension validation
2. File size limit enforcement
3. MIME type checking
4. Temporary file cleanup
5. Database record creation
6. R2 upload success

## Integration Points for Future Workers

### Worker Input (Future)
```json
{
  "job_id": "uuid",
  "video_id": "uuid",
  "r2_url": "https://cdn.example.com/...",
  "r2_key": "videos/12345678/2026/06/video.mp4"
}
```

### Worker Output (Future)
```json
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "progress": 100,
  "results": {
    "detections": [...],
    "metadata": {...}
  }
}
```

## Troubleshooting

### R2 Credentials Error
- Check `.env` file has all R2_* variables
- Verify credentials are correct
- Check API token permissions

### File Upload Fails
- Verify file extension is allowed
- Check file size < MAX_VIDEO_SIZE_BYTES
- Check MIME type starts with `video/`

### Database Error
- Run migration: `alembic upgrade head`
- Check PostgreSQL connection
- Verify database schema

### Temporary File Cleanup
- Files cleaned up on success
- Ensure `/tmp` directory is writable
- Check disk space availability

## Support

See full documentation in:
- `/docs/R2_ARCHITECTURE.md` - Detailed architecture
- `/backend_fastapi/SPRINT_2B_README.md` - Implementation guide
