# Sprint 2B - Cloudflare R2 Integration - Implementation Guide

## Overview

This document details the complete implementation of the Cloudflare R2 integration for video upload pipeline. This is a production-ready foundation for video management with infrastructure prepared for future AI processing.

## What Was Implemented

### ✅ Core Infrastructure

1. **R2 Service** (`app/core/r2.py`)
   - Boto3 S3-compatible client
   - async/await support
   - Methods: upload_file, delete_file, generate_presigned_url, file_exists, get_public_url
   - Comprehensive error handling and logging

2. **Configuration** (`app/core/config.py`)
   - R2 credentials settings (account_id, access_key, secret_key, bucket, public_url)
   - Upload limits (max_video_size_bytes: 500MB)
   - Allowed extensions (mp4, mov, avi, mkv)

3. **Video Upload Service** (`app/services/video_upload_service.py`)
   - Complete upload workflow orchestration
   - File validation (extension, size, MIME type)
   - R2 key generation with structure: `videos/{gk_id}/{year}/{month}/{filename}`
   - Database record creation
   - Temporary file cleanup
   - Error handling and logging

### ✅ Database Updates

1. **Video Model Enhancements**
   ```python
   - original_filename: str
   - mime_type: str
   - file_size_bytes: int
   - r2_bucket: str
   - r2_key: str
   - r2_url: str
   - uploaded_at: DateTime
   - upload_status: Enum (PENDING, UPLOADED, PROCESSING, COMPLETED, FAILED)
   ```

2. **ProcessingJob Model Enhancements**
   ```python
   - job_type: str
   - worker_id: str
   - retry_count: int
   - status: Enum (PENDING, RUNNING, COMPLETED, FAILED)
   ```

3. **Migration File** (`alembic/versions/003_add_r2_integration.py`)
   - Adds all new columns
   - Creates enum types for upload_status and job status
   - Includes rollback logic

### ✅ API Endpoints

1. **Video Upload**
   - `POST /api/v1/videos/upload`
   - Accepts multipart file upload
   - Validates file and uploads to R2
   - Returns: video_id, job_id, status, r2_key, r2_url

2. **Video Status**
   - `GET /api/v1/videos/{id}/status`
   - Returns: video_status, job_status, progress, r2_url

3. **Processing Job Status**
   - `GET /api/v1/processing-jobs/{id}/status`
   - Returns: job_id, video_id, status, progress, started_at, completed_at, error_message

### ✅ Documentation

1. **R2_ARCHITECTURE.md** - Complete architectural overview
   - System components
   - Database schema
   - API specifications
   - Security considerations
   - Future AI worker integration points
   - Monitoring and logging strategy

2. **R2_QUICK_REFERENCE.md** - Quick reference guide
   - Key files
   - Upload flow
   - API examples with curl
   - Configuration setup
   - Testing procedures
   - Troubleshooting guide

## Modified Files Summary

### Created Files

```
app/core/r2.py                                    (R2 Service)
app/services/video_upload_service.py              (Video Upload Orchestration)
alembic/versions/003_add_r2_integration.py        (Database Migration)
docs/R2_ARCHITECTURE.md                           (Detailed Documentation)
docs/R2_QUICK_REFERENCE.md                        (Quick Reference)
```

### Modified Files

```
app/core/config.py                                (Added R2 settings)
app/models/models.py                              (Enhanced Video & ProcessingJob)
app/schemas/schemas.py                            (Updated schemas with new fields)
app/repositories/repositories.py                  (Updated create methods)
app/api/v1/videos.py                              (Added upload & status endpoints)
app/api/v1/processing_jobs.py                     (Added status endpoint)
backend_fastapi/requirements.txt                  (Added boto3)
backend_fastapi/.env.example                      (Added R2 env vars)
```

## Database Schema Changes

### New Columns - videos table

```sql
ALTER TABLE videos ADD COLUMN original_filename VARCHAR;
ALTER TABLE videos ADD COLUMN mime_type VARCHAR;
ALTER TABLE videos ADD COLUMN file_size_bytes INTEGER;
ALTER TABLE videos ADD COLUMN r2_bucket VARCHAR;
ALTER TABLE videos ADD COLUMN r2_url VARCHAR;
ALTER TABLE videos ADD COLUMN uploaded_at TIMESTAMP WITH TIME ZONE;

-- Convert upload_status to ENUM
CREATE TYPE upload_status_enum AS ENUM ('PENDING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED');
```

### New Columns - processing_jobs table

```sql
ALTER TABLE processing_jobs ADD COLUMN job_type VARCHAR;
ALTER TABLE processing_jobs ADD COLUMN worker_id VARCHAR;
ALTER TABLE processing_jobs ADD COLUMN retry_count INTEGER DEFAULT 0;

-- Convert status to ENUM
CREATE TYPE processing_job_status_enum AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED');
```

## Environment Variables Required

```env
# R2 Configuration
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=goalkeeper-ai-videos
R2_PUBLIC_URL=https://videos.example.com

# Upload Configuration
MAX_VIDEO_SIZE_BYTES=524288000
ALLOWED_VIDEO_EXTENSIONS=mp4,mov,avi,mkv
```

## Installation Steps

### 1. Update Dependencies
```bash
cd backend_fastapi
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with Cloudflare R2 credentials
```

### 3. Run Database Migration
```bash
alembic upgrade head
```

### 4. Start Application
```bash
uvicorn app.main:app --reload
```

## API Usage Examples

### Upload Video

```bash
curl -X POST "http://localhost:8001/api/v1/videos/upload" \
  -F "file=@training_video.mp4" \
  -F "training_session_id=550e8400-e29b-41d4-a716-446655440000"
```

Response (201):
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "status": "UPLOADED",
  "r2_key": "videos/550e8400/2026/06/training_video_20260608_160000.mp4",
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

### Check Video Status

```bash
curl "http://localhost:8001/api/v1/videos/123e4567-e89b-12d3-a456-426614174000/status"
```

Response (200):
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_status": "PROCESSING",
  "job_status": "RUNNING",
  "progress": 35.5,
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

### Check Job Status

```bash
curl "http://localhost:8001/api/v1/processing-jobs/987f6543-a21b-98d7-c654-321098765432/status"
```

Response (200):
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "RUNNING",
  "progress": 35.5,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": null,
  "error_message": null
}
```

## Upload Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Video Upload Pipeline                       │
└─────────────────────────────────────────────────────────────────┘

Client
  │
  ├─→ POST /videos/upload
  │   (multipart: file + training_session_id)
  │
  └─→ FastAPI Endpoint
      │
      ├─→ Validate File
      │   ├─ Extension (mp4, mov, avi, mkv)
      │   ├─ Size (< 500MB default)
      │   └─ MIME type (video/*)
      │
      ├─→ VideoUploadService
      │   │
      │   ├─→ Save temporarily
      │   │
      │   ├─→ Generate R2 key
      │   │   videos/{gk_id}/{year}/{month}/{filename}
      │   │
      │   ├─→ Upload to R2
      │   │   │
      │   │   └─→ Cloudflare R2
      │   │       └─→ CDN Cache
      │   │
      │   ├─→ Create Video Record
      │   │   upload_status = UPLOADED
      │   │
      │   ├─→ Create ProcessingJob
      │   │   status = PENDING
      │   │
      │   └─→ Cleanup temp file
      │
      └─→ Return Response
          ├─ video_id
          ├─ job_id
          ├─ r2_key
          └─ r2_url

Client receives:
{
  "video_id": "...",
  "job_id": "...",
  "status": "UPLOADED",
  "r2_key": "...",
  "r2_url": "..."
}

Client can then:
- Monitor status: GET /videos/{video_id}/status
- Check job: GET /processing-jobs/{job_id}/status
- Access video: Use r2_url for direct playback
```

## R2 Storage Structure

```
R2 Bucket: goalkeeper-ai-videos
│
└─ videos/
   │
   ├─ 550e8400/          (goalkeeper_id - first 8 chars of UUID)
   │  │
   │  ├─ 2026/
   │  │  │
   │  │  ├─ 01/
   │  │  │  ├─ training_001_20260101_120000.mp4
   │  │  │  ├─ training_002_20260101_140000.mov
   │  │  │  └─ ...
   │  │  │
   │  │  ├─ 02/
   │  │  │  └─ ...
   │  │  │
   │  │  ├─ 06/
   │  │  │  ├─ training_001_20260608_160000.mp4
   │  │  │  └─ ...
   │  │  │
   │  │  └─ ...
   │  │
   │  └─ 2025/
   │     └─ ...
   │
   └─ 1234abcd/          (another goalkeeper)
      └─ ...
```

## Cloudflare R2 Configuration

### Create Bucket

1. Log in to Cloudflare Dashboard
2. Go to R2 Storage
3. Create Bucket: `goalkeeper-ai-videos`
4. Copy Account ID

### Generate API Token

1. Go to R2 Settings
2. Create API Token
3. Permissions: Edit (Objects in bucket)
4. Copy Access Key ID and Secret Access Key

### Setup Public URL (Optional)

1. In bucket settings
2. Configure custom domain
3. Use CNAME pointing to R2
4. Set `R2_PUBLIC_URL` in environment

## Security Features

### File Validation
- Extension whitelist (mp4, mov, avi, mkv)
- MIME type verification
- File size enforcement
- Path traversal prevention (unique filenames)

### Access Control
- Presigned URLs for temporary access
- Public URLs for client playback
- HTTPS-only connections
- API token scoping

### Data Protection
- Encryption at rest (Cloudflare R2)
- Secure temporary file handling
- Comprehensive error logging
- Automatic cleanup on failure

## Future AI Worker Integration

The system is architected to support AI processing workers:

### Future Architecture

```
Video Upload → R2 → Queue → Cloudflare Worker → YOLO/OpenCV → Results

ProcessingJob states:
PENDING  → (worker picks up)
RUNNING  → (processing)
COMPLETED → (results stored)
```

### Integration Points Prepared

1. **Worker Input Structure:**
   - job_id, video_id, r2_url, r2_key ready in ProcessingJob
   - Worker can fetch video from r2_url

2. **Progress Tracking:**
   - progress field (0-100) ready for updates
   - started_at and completed_at fields ready

3. **Error Handling:**
   - retry_count field for failed job retry
   - error_message field for failure details
   - status tracking for state management

4. **Result Storage:**
   - PostgreSQL for structured data
   - R2 for large result files (video analysis output)

## Monitoring & Logging

### Key Metrics

- Upload success rate
- Average upload time
- File size distribution
- Storage utilization
- Job completion rate
- Processing duration

### Logs

All operations logged with:
- Timestamp
- Operation type
- Result (success/failure)
- Relevant IDs (video_id, job_id, r2_key)
- Error details if failed

## Testing Recommendations

### Unit Tests
- R2Service methods
- File validation logic
- Key generation
- Error scenarios

### Integration Tests
- Full upload workflow
- Database record creation
- R2 connectivity
- Job creation and status

### Load Tests
- Concurrent uploads
- Large file handling
- Database performance
- R2 rate limits

## Troubleshooting

### R2 Connection Issues
- Verify R2_ACCOUNT_ID is correct
- Check access key credentials
- Confirm bucket name is correct
- Test with Cloudflare console

### Upload Failures
- Check file extension is allowed
- Verify file size < 500MB
- Ensure MIME type is video/*
- Check disk space for temp files

### Database Issues
- Run: `alembic upgrade head`
- Verify PostgreSQL connection
- Check schema exists

## Next Steps

### Immediate
1. Deploy to staging environment
2. Test with real video files
3. Monitor performance metrics
4. Collect user feedback

### Short Term
1. Implement AI worker integration
2. Add video analysis features
3. Build dashboard for monitoring
4. Setup alerts and notifications

### Long Term
1. Video encoding/transcoding
2. Advanced analytics
3. Multi-region deployment
4. Performance optimization

## Support & Documentation

- Full architecture: `/docs/R2_ARCHITECTURE.md`
- Quick reference: `/docs/R2_QUICK_REFERENCE.md`
- API docs: `/backend_fastapi/API_ENDPOINTS.md` (auto-generated from FastAPI)
- Code comments: Check implementation files for inline documentation

## Version Information

- Sprint: 2B
- Implementation Date: 2026-06-08
- Framework: FastAPI 0.104.1
- Database: PostgreSQL 13+
- Storage: Cloudflare R2
- Python: 3.10+

## Checklist for Deployment

- [ ] All environment variables configured
- [ ] Database migration applied (`alembic upgrade head`)
- [ ] R2 credentials verified and working
- [ ] Requirements installed (`pip install -r requirements.txt`)
- [ ] Application starts without errors
- [ ] Upload endpoint responds to health check
- [ ] Can upload test file successfully
- [ ] File appears in R2 bucket
- [ ] Database records created correctly
- [ ] Status endpoints return correct data
- [ ] Error handling tested
- [ ] Logging verified
- [ ] Documentation reviewed

## Conclusion

Sprint 2B delivers a production-ready video upload infrastructure leveraging Cloudflare R2 for reliable, scalable storage. The system is designed to seamlessly integrate with future AI processing workers while maintaining security, reliability, and performance.
