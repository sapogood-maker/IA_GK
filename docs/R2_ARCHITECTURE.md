# Cloudflare R2 Integration Architecture

## Overview

This document describes the Cloudflare R2 integration for the Goalkeeper AI video upload pipeline. R2 provides S3-compatible storage for video files with built-in CDN delivery.

## Architecture Components

### 1. R2 Service (`app/core/r2.py`)

The R2Service is a reusable service for managing file operations in Cloudflare R2.

**Key Functions:**

- `upload_file(file_path, r2_key, content_type)` - Upload file to R2
- `delete_file(r2_key)` - Delete file from R2
- `generate_presigned_url(r2_key, expiration_seconds)` - Generate time-limited access URLs
- `file_exists(r2_key)` - Check if file exists in R2
- `get_public_url(r2_key)` - Get public URL for file

**Implementation Details:**

- Uses boto3 with S3-compatible endpoint
- Endpoint URL: `https://{ACCOUNT_ID}.r2.cloudflarestorage.com`
- Region: `auto` (Cloudflare automatically selects nearest region)
- All operations are async-compatible

### 2. Video Upload Service (`app/services/video_upload_service.py`)

The VideoUploadService orchestrates the complete video upload workflow.

**Workflow:**

```
1. Validate file
   ├── Check file extension (mp4, mov, avi, mkv)
   ├── Validate MIME type
   └── Check file size

2. Save file temporarily

3. Generate R2 key based on structure:
   videos/{goalkeeper_id}/{year}/{month}/{unique_filename}

4. Upload to R2

5. Create Video record in database
   ├── Set upload_status = UPLOADED
   └── Store R2 metadata

6. Create ProcessingJob record
   ├── Set status = PENDING
   └── Initialize progress = 0

7. Clean up temporary file
```

**Key Methods:**

- `upload_video(training_session_id, file)` - Main upload orchestration
- `get_video_status(video_id)` - Get video and job status
- `get_job_status(job_id)` - Get detailed job information

### 3. Database Schema

#### Video Model

```python
id: UUID (Primary Key)
training_session_id: UUID (Foreign Key)
filename: str (Generated unique name)
original_filename: str (User's original filename)
mime_type: str (video/mp4, video/quicktime, etc.)
file_size_bytes: int
duration_seconds: float (Optional, for future use)
r2_bucket: str (Bucket name)
r2_key: str (Path in bucket)
r2_url: str (Public URL)
upload_status: Enum (PENDING, UPLOADED, PROCESSING, COMPLETED, FAILED)
uploaded_at: DateTime
created_at: DateTime
updated_at: DateTime
```

#### ProcessingJob Model

```python
id: UUID (Primary Key)
video_id: UUID (Foreign Key)
job_type: str (e.g., "video_processing")
worker_id: str (For future worker assignment)
status: Enum (PENDING, RUNNING, COMPLETED, FAILED)
progress: float (0-100)
retry_count: int
started_at: DateTime
completed_at: DateTime
error_message: str
created_at: DateTime
updated_at: DateTime
```

#### Status Enums

**UploadStatus:**
- `PENDING` - Waiting to be uploaded
- `UPLOADED` - Successfully uploaded to R2
- `PROCESSING` - Being processed (AI analysis)
- `COMPLETED` - Upload and processing complete
- `FAILED` - Upload or processing failed

**ProcessingJobStatus:**
- `PENDING` - Job created, waiting to start
- `RUNNING` - Job is actively processing
- `COMPLETED` - Job finished successfully
- `FAILED` - Job failed with error

### 4. R2 Storage Structure

```
videos/
├── {goalkeeper_id}/
│   ├── 2026/
│   │   ├── 01/
│   │   │   ├── training_001_20260101_120000.mp4
│   │   │   └── training_002_20260102_140000.mov
│   │   ├── 02/
│   │   └── ...
│   └── 2025/
└── {goalkeeper_id}/
    └── ...
```

**Path Components:**
- `videos/` - Bucket prefix
- `{goalkeeper_id}` - 8-character hex from training session UUID
- `{year}/{month}` - Organization by date
- `{filename}_{timestamp}` - Unique filename with timestamp

### 5. API Endpoints

#### Upload Video

```
POST /api/v1/videos/upload
Content-Type: multipart/form-data

Query Parameters:
- training_session_id: UUID (required)

File Upload:
- file: Binary video file

Response (201 Created):
{
  "video_id": "uuid",
  "job_id": "uuid",
  "status": "UPLOADED",
  "r2_key": "videos/12345678/2026/06/training_001_20260608_160000.mp4",
  "r2_url": "https://cdn.example.com/videos/12345678/2026/06/training_001_20260608_160000.mp4"
}
```

#### Get Video Status

```
GET /api/v1/videos/{video_id}/status

Response (200 OK):
{
  "video_id": "uuid",
  "video_status": "PROCESSING",
  "job_status": "RUNNING",
  "progress": 35.5,
  "r2_url": "https://cdn.example.com/videos/..."
}
```

#### Get Processing Job Status

```
GET /api/v1/processing-jobs/{job_id}/status

Response (200 OK):
{
  "job_id": "uuid",
  "video_id": "uuid",
  "status": "RUNNING",
  "progress": 35.5,
  "started_at": "2026-06-08T16:00:00+00:00",
  "completed_at": null,
  "error_message": null
}
```

## Configuration

### Environment Variables

```env
# R2 Account Configuration
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key
R2_BUCKET_NAME=goalkeeper-ai-videos
R2_PUBLIC_URL=https://videos.example.com

# Upload Configuration
MAX_VIDEO_SIZE_BYTES=524288000  # 500 MB
ALLOWED_VIDEO_EXTENSIONS=mp4,mov,avi,mkv
```

### Cloudflare R2 Setup

1. **Create R2 Account and Bucket:**
   - Go to Cloudflare R2 dashboard
   - Create new bucket: `goalkeeper-ai-videos`
   - Note Account ID

2. **Generate API Token:**
   - Create API token with R2 permissions
   - Permissions needed: `All` on Objects in bucket
   - Note Access Key ID and Secret Access Key

3. **Setup Custom Domain (Optional):**
   - Configure custom domain in R2 bucket settings
   - Set `R2_PUBLIC_URL` to your domain
   - Example: `https://videos.example.com`

4. **CDN Configuration:**
   - Enable Cloudflare CDN caching
   - Set cache rules for video files
   - Configure cache expiration

## Security Considerations

### File Validation

1. **Extension Validation:** Only allow mp4, mov, avi, mkv files
2. **MIME Type Checking:** Verify `Content-Type` header matches video
3. **File Size Limits:** Enforce maximum file size (500 MB default)
4. **Path Traversal Prevention:** Generated filenames prevent directory traversal

### Access Control

1. **Presigned URLs:** Use for temporary, time-limited access
2. **Public URLs:** Standard R2 public URLs for client downloads
3. **HTTPS Only:** All R2 endpoints use HTTPS
4. **Authentication:** API tokens scoped to specific bucket/permissions

### Data Security

1. **Encryption:** Cloudflare R2 encrypts data at rest
2. **Versioning:** Enable bucket versioning for recovery
3. **Logging:** Enable access logging for audit trail
4. **Backup:** Regular backups to secondary storage

## Future AI Worker Integration

### Planned Architecture

```
Upload → R2 Storage → Queue → Cloudflare Workers → AI Processing

1. Video uploaded to R2
2. ProcessingJob created with status=PENDING
3. Worker polls for PENDING jobs
4. Worker processes video (YOLO/OpenCV)
5. Results stored in database
6. ProcessingJob status updated to COMPLETED
```

### Integration Points

**Worker Trigger:**
- Webhook triggered on new video upload
- Or: Scheduled job polling queue every N seconds

**Processing Pipeline:**
```python
# POST /process-video (Future implementation)
{
  "job_id": "uuid",
  "video_id": "uuid",
  "r2_url": "https://cdn.example.com/...",
  "r2_key": "videos/..."
}
```

**Result Storage:**
```python
# Update ProcessingJob
{
  "status": "COMPLETED",
  "progress": 100,
  "completed_at": "2026-06-08T16:30:00+00:00"
}

# Store analysis results in:
# - PostgreSQL tables (for queries)
# - R2 bucket (for raw data)
```

## Monitoring and Logging

### Metrics to Track

1. **Upload Metrics:**
   - Total uploads
   - Upload success rate
   - Upload duration
   - Average file size

2. **Storage Metrics:**
   - Total storage used
   - Bandwidth consumption
   - Request count
   - Error rate

3. **Processing Metrics:**
   - Jobs pending
   - Jobs completed
   - Average processing time
   - Failure rate

### Logging

```python
logger.info(f"Successfully uploaded video {video_id} to R2: {r2_key}")
logger.error(f"Error uploading to R2: {error}")
logger.warning("R2 credentials not fully configured")
```

## Error Handling

### Common Errors

1. **File Too Large:** Return 400 with message about size limit
2. **Invalid Extension:** Return 400 with allowed extensions list
3. **R2 Connection Failed:** Return 500 with retry guidance
4. **Missing Credentials:** Return 500 with configuration error
5. **Duplicate File:** Generate unique filename with timestamp

### Recovery

- Temporary files cleaned up on failure
- Failed uploads logged for debugging
- Job retry mechanism (retry_count field)
- Graceful degradation if R2 unavailable

## Performance Optimization

### Chunked Upload (Future)

For large files (>500MB):
```python
# Implement multipart upload
# Max 10 GB per part
# Upload in parallel
```

### Caching Strategy

- Browser cache: 24 hours
- CDN cache: 7 days
- Origin cache: No cache (fresh from R2)

### Concurrent Uploads

- Support multiple simultaneous uploads
- Queue management for large volumes
- Resource pooling and reuse

## Disaster Recovery

### Backup Strategy

1. **Versioning:** Enable R2 bucket versioning
2. **Redundancy:** Store copies in secondary location
3. **Restore Procedure:** Document recovery steps
4. **Testing:** Periodic restore drills

### Failover

1. **Primary Failure:** Switch to backup storage
2. **Database Failure:** Recover from backup
3. **Service Restart:** Automatic reconnection

## Testing

### Unit Tests

- R2Service methods
- File validation logic
- Path generation
- Error handling

### Integration Tests

- Full upload workflow
- Database record creation
- Job creation and status
- Error scenarios

### Load Tests

- Upload concurrent files
- Large file handling
- Error condition recovery

## References

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [boto3 S3 API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [FastAPI File Upload](https://fastapi.tiangolo.com/request-files/)
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
