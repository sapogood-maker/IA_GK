# Sprint 2B - API Endpoints Reference

## Overview

This document provides a complete reference for all Sprint 2B API endpoints related to video upload and processing job management.

## Video Upload Endpoints

### 1. Upload Video File

**Endpoint:** `POST /api/v1/videos/upload`

**Purpose:** Upload a video file to Cloudflare R2 and create associated database records

**Request:**
```
Method: POST
Content-Type: multipart/form-data

Query Parameters:
- training_session_id (UUID, required): ID of the training session

File:
- file (binary, required): Video file (mp4, mov, avi, mkv)

Maximum file size: 500 MB (configurable via MAX_VIDEO_SIZE_BYTES)
```

**Example Request:**
```bash
curl -X POST "http://localhost:8001/api/v1/videos/upload" \
  -F "file=@training_video.mp4" \
  -F "training_session_id=550e8400-e29b-41d4-a716-446655440000"
```

**Response (201 Created):**
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "status": "UPLOADED",
  "r2_key": "videos/550e8400/2026/06/training_video_20260608_160000.mp4",
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| video_id | UUID | Unique identifier for uploaded video |
| job_id | UUID | Unique identifier for processing job |
| status | String | Upload status: UPLOADED |
| r2_key | String | Path in R2 bucket |
| r2_url | String | Public CDN URL for video access |

**Error Responses:**
- `400 Bad Request` - Invalid file (wrong extension, too large, wrong MIME type)
- `404 Not Found` - Training session not found
- `500 Internal Server Error` - R2 upload failed or server error

**Example Errors:**
```json
{
  "detail": "Invalid file extension. Allowed: mp4, mov, avi, mkv"
}
```

```json
{
  "detail": "File too large. Max size: 500 MB"
}
```

---

### 2. Get Video Status

**Endpoint:** `GET /api/v1/videos/{video_id}/status`

**Purpose:** Get current video upload and processing job status

**Request:**
```
Method: GET
Path Parameter:
- video_id (UUID, required): ID of the video
```

**Example Request:**
```bash
curl "http://localhost:8001/api/v1/videos/123e4567-e89b-12d3-a456-426614174000/status"
```

**Response (200 OK):**
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_status": "PROCESSING",
  "job_status": "RUNNING",
  "progress": 35.5,
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| video_id | UUID | Video identifier |
| video_status | String | Video status: PENDING, UPLOADED, PROCESSING, COMPLETED, FAILED |
| job_status | String | Job status: PENDING, RUNNING, COMPLETED, FAILED |
| progress | Float | Processing progress 0-100 |
| r2_url | String | Public URL to video |

**Status Values:**

Video Status:
- `PENDING` - Waiting to be uploaded
- `UPLOADED` - Successfully uploaded to R2
- `PROCESSING` - Being processed (AI analysis)
- `COMPLETED` - Upload and processing complete
- `FAILED` - Upload or processing failed

Job Status:
- `PENDING` - Job created, waiting to start
- `RUNNING` - Job actively processing
- `COMPLETED` - Job finished successfully
- `FAILED` - Job failed with error

**Example Responses:**

Status: Upload Complete
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_status": "UPLOADED",
  "job_status": "PENDING",
  "progress": 0.0,
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

Status: Processing
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_status": "PROCESSING",
  "job_status": "RUNNING",
  "progress": 45.5,
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

Status: Complete
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "video_status": "COMPLETED",
  "job_status": "COMPLETED",
  "progress": 100.0,
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4"
}
```

**Error Responses:**
- `404 Not Found` - Video not found

---

### 3. List Videos (with optional filtering)

**Endpoint:** `GET /api/v1/videos`

**Purpose:** List all videos or filter by training session

**Request:**
```
Method: GET

Query Parameters (optional):
- training_session_id (UUID): Filter by training session ID
```

**Example Requests:**
```bash
# Get all videos
curl "http://localhost:8001/api/v1/videos"

# Get videos for specific training session
curl "http://localhost:8001/api/v1/videos?training_session_id=550e8400-e29b-41d4-a716-446655440000"
```

**Response (200 OK):**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "training_session_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "training_video_20260608_160000.mp4",
    "original_filename": "training_video.mp4",
    "mime_type": "video/mp4",
    "file_size_bytes": 125456789,
    "duration_seconds": 3600.0,
    "r2_bucket": "goalkeeper-ai-videos",
    "r2_key": "videos/550e8400/2026/06/training_video_20260608_160000.mp4",
    "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4",
    "upload_status": "PROCESSING",
    "uploaded_at": "2026-06-08T16:00:00+00:00",
    "created_at": "2026-06-08T16:00:00+00:00",
    "updated_at": "2026-06-08T16:05:00+00:00"
  }
]
```

---

### 4. Get Video Details

**Endpoint:** `GET /api/v1/videos/{video_id}`

**Purpose:** Get detailed information about a specific video

**Request:**
```
Method: GET
Path Parameter:
- video_id (UUID, required): ID of the video
```

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "training_session_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "training_video_20260608_160000.mp4",
  "original_filename": "training_video.mp4",
  "mime_type": "video/mp4",
  "file_size_bytes": 125456789,
  "duration_seconds": 3600.0,
  "r2_bucket": "goalkeeper-ai-videos",
  "r2_key": "videos/550e8400/2026/06/training_video_20260608_160000.mp4",
  "r2_url": "https://videos.example.com/videos/550e8400/2026/06/training_video_20260608_160000.mp4",
  "upload_status": "PROCESSING",
  "uploaded_at": "2026-06-08T16:00:00+00:00",
  "created_at": "2026-06-08T16:00:00+00:00",
  "updated_at": "2026-06-08T16:05:00+00:00"
}
```

---

### 5. Update Video

**Endpoint:** `PUT /api/v1/videos/{video_id}`

**Purpose:** Update video metadata (status updates, metadata)

**Request:**
```
Method: PUT
Path Parameter:
- video_id (UUID, required): ID of the video

Body (JSON):
{
  "upload_status": "COMPLETED",
  "duration_seconds": 3600.0,
  "mime_type": "video/mp4"
}
```

**Response (200 OK):** Updated video object

---

### 6. Delete Video

**Endpoint:** `DELETE /api/v1/videos/{video_id}`

**Purpose:** Delete video record (should also delete from R2)

**Request:**
```
Method: DELETE
Path Parameter:
- video_id (UUID, required): ID of the video
```

**Response (204 No Content):** Empty response

---

## Processing Job Endpoints

### 1. Get Processing Job Status

**Endpoint:** `GET /api/v1/processing-jobs/{job_id}/status`

**Purpose:** Get detailed status of a processing job

**Request:**
```
Method: GET
Path Parameter:
- job_id (UUID, required): ID of the processing job
```

**Example Request:**
```bash
curl "http://localhost:8001/api/v1/processing-jobs/987f6543-a21b-98d7-c654-321098765432/status"
```

**Response (200 OK):**
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "RUNNING",
  "progress": 45.5,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": null,
  "error_message": null
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| job_id | UUID | Job identifier |
| video_id | UUID | Associated video ID |
| status | String | Job status: PENDING, RUNNING, COMPLETED, FAILED |
| progress | Float | Progress 0-100 |
| started_at | DateTime | When job started |
| completed_at | DateTime | When job completed (null if running) |
| error_message | String | Error details if failed |

**Example Responses:**

Pending:
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "progress": 0.0,
  "started_at": null,
  "completed_at": null,
  "error_message": null
}
```

Running:
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "RUNNING",
  "progress": 65.3,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": null,
  "error_message": null
}
```

Completed:
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "COMPLETED",
  "progress": 100.0,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": "2026-06-08T16:35:00+00:00",
  "error_message": null
}
```

Failed:
```json
{
  "job_id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "FAILED",
  "progress": 25.0,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": "2026-06-08T16:15:00+00:00",
  "error_message": "Frame extraction failed: Invalid codec"
}
```

**Error Responses:**
- `404 Not Found` - Job not found

---

### 2. List Processing Jobs (with optional filtering)

**Endpoint:** `GET /api/v1/processing-jobs`

**Purpose:** List processing jobs with optional filtering

**Request:**
```
Method: GET

Query Parameters (optional):
- video_id (UUID): Filter by video ID
- status (String): Filter by status (PENDING, RUNNING, COMPLETED, FAILED)
```

**Example Requests:**
```bash
# Get all jobs
curl "http://localhost:8001/api/v1/processing-jobs"

# Get jobs for specific video
curl "http://localhost:8001/api/v1/processing-jobs?video_id=123e4567-e89b-12d3-a456-426614174000"

# Get running jobs
curl "http://localhost:8001/api/v1/processing-jobs?status=RUNNING"
```

**Response (200 OK):** Array of job objects

---

### 3. Get Processing Job Details

**Endpoint:** `GET /api/v1/processing-jobs/{job_id}`

**Purpose:** Get full processing job record

**Request:**
```
Method: GET
Path Parameter:
- job_id (UUID, required): ID of the processing job
```

**Response (200 OK):**
```json
{
  "id": "987f6543-a21b-98d7-c654-321098765432",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "video_processing",
  "worker_id": null,
  "status": "RUNNING",
  "progress": 45.5,
  "retry_count": 0,
  "started_at": "2026-06-08T16:05:00+00:00",
  "completed_at": null,
  "error_message": null,
  "created_at": "2026-06-08T16:00:00+00:00",
  "updated_at": "2026-06-08T16:05:00+00:00"
}
```

---

### 4. Create Processing Job

**Endpoint:** `POST /api/v1/processing-jobs`

**Purpose:** Create a new processing job for a video

**Request:**
```
Method: POST
Content-Type: application/json

Body:
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "video_processing",
  "worker_id": null,
  "status": "PENDING",
  "progress": 0.0,
  "retry_count": 0,
  "error_message": null
}
```

**Response (201 Created):** Created job object

---

### 5. Update Processing Job

**Endpoint:** `PUT /api/v1/processing-jobs/{job_id}`

**Purpose:** Update job status and progress (typically called by workers)

**Request:**
```
Method: PUT
Path Parameter:
- job_id (UUID, required): ID of the processing job

Body (JSON):
{
  "status": "RUNNING",
  "progress": 45.5,
  "started_at": "2026-06-08T16:05:00+00:00"
}
```

**Common Update Scenarios:**

Start Job:
```json
{
  "status": "RUNNING",
  "started_at": "2026-06-08T16:05:00+00:00"
}
```

Update Progress:
```json
{
  "progress": 75.0
}
```

Complete Job:
```json
{
  "status": "COMPLETED",
  "progress": 100.0,
  "completed_at": "2026-06-08T16:35:00+00:00"
}
```

Job Failed:
```json
{
  "status": "FAILED",
  "completed_at": "2026-06-08T16:15:00+00:00",
  "error_message": "Frame extraction failed: Invalid codec"
}
```

**Response (200 OK):** Updated job object

---

### 6. Delete Processing Job

**Endpoint:** `DELETE /api/v1/processing-jobs/{job_id}`

**Purpose:** Delete processing job record

**Request:**
```
Method: DELETE
Path Parameter:
- job_id (UUID, required): ID of the processing job
```

**Response (204 No Content):** Empty response

---

## Complete Workflow Example

### Upload and Monitor Video

```bash
# 1. Upload video
UPLOAD_RESPONSE=$(curl -X POST "http://localhost:8001/api/v1/videos/upload" \
  -F "file=@training.mp4" \
  -F "training_session_id=550e8400-e29b-41d4-a716-446655440000")

VIDEO_ID=$(echo $UPLOAD_RESPONSE | jq -r '.video_id')
JOB_ID=$(echo $UPLOAD_RESPONSE | jq -r '.job_id')

echo "Video uploaded: $VIDEO_ID"
echo "Job created: $JOB_ID"

# 2. Check initial status
curl "http://localhost:8001/api/v1/videos/$VIDEO_ID/status"

# Output should show:
# - video_status: UPLOADED
# - job_status: PENDING
# - progress: 0

# 3. Wait and check job status periodically
for i in {1..10}; do
  echo "Check $i:"
  curl "http://localhost:8001/api/v1/processing-jobs/$JOB_ID/status"
  sleep 5
done

# 4. Final check
curl "http://localhost:8001/api/v1/videos/$VIDEO_ID/status"

# Output should show:
# - video_status: COMPLETED
# - job_status: COMPLETED
# - progress: 100
```

---

## Error Codes Reference

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Delete successful |
| 400 | Bad Request | Invalid file/request |
| 404 | Not Found | Resource not found |
| 500 | Server Error | Server error or R2 failure |

---

## Rate Limiting

Currently no rate limiting implemented. Future versions should add:
- Request rate limiting per user/IP
- File upload throttling
- Concurrent upload limits

---

## Pagination

Currently all list endpoints return all records. Future versions should add:
- Limit and offset parameters
- Page number and size
- Sorting options

---

## Additional Resources

- **Architecture Details:** See `docs/R2_ARCHITECTURE.md`
- **Quick Reference:** See `docs/R2_QUICK_REFERENCE.md`
- **Implementation Guide:** See `backend_fastapi/SPRINT_2B_README.md`
- **Interactive Docs:** Visit `http://localhost:8001/docs` when running

---

## Version Information

- **Sprint:** 2B
- **Date:** 2026-06-08
- **API Version:** v1
- **Framework:** FastAPI 0.104.1
