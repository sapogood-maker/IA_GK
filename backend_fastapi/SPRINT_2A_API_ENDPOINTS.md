# Sprint 2A API Endpoints Documentation

## Overview

This document provides detailed API endpoint specifications for the three new entities added in Sprint 2A:
- Training Sessions
- Videos  
- Processing Jobs

## Base URL
```
http://localhost:8001/api/v1
```

## Content Type
All endpoints expect and return JSON with `Content-Type: application/json`

---

## Training Sessions

### 1. Create Training Session

**Endpoint:** `POST /training-sessions`

**Description:** Create a new training session record.

**Request Body:**
```json
{
  "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
  "coach_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Penalty Kicks Drill",
  "session_type": "drill",
  "session_date": "2026-06-08T10:30:00Z",
  "notes": "Focused on one-on-one scenarios"
}
```

**Request Fields:**
- `goalkeeper_id` (required): UUID of the goalkeeper
- `coach_id` (optional): UUID of the coach conducting the session
- `title` (required): Name of the training session
- `session_type` (required): Type of session (e.g., "drill", "match_analysis", "technical_training")
- `session_date` (required): ISO 8601 datetime when session occurred
- `notes` (optional): Additional notes about the session

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
  "coach_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Penalty Kicks Drill",
  "session_type": "drill",
  "session_date": "2026-06-08T10:30:00+00:00",
  "notes": "Focused on one-on-one scenarios",
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": null
}
```

**Error Responses:**
- `404 Not Found`: If goalkeeper_id or coach_id doesn't exist
- `422 Unprocessable Entity`: Validation error (e.g., missing required field)

---

### 2. List Training Sessions

**Endpoint:** `GET /training-sessions`

**Description:** List all training sessions with optional filtering.

**Query Parameters:**
- `goalkeeper_id` (optional): Filter sessions by goalkeeper UUID
- `coach_id` (optional): Filter sessions by coach UUID

**Example Requests:**
```
GET /training-sessions                                    # All sessions
GET /training-sessions?goalkeeper_id=550e8400-e29b-...   # Sessions for specific goalkeeper
GET /training-sessions?coach_id=550e8400-e29b-...        # Sessions by specific coach
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
    "coach_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Penalty Kicks Drill",
    "session_type": "drill",
    "session_date": "2026-06-08T10:30:00+00:00",
    "notes": "Focused on one-on-one scenarios",
    "created_at": "2026-06-08T16:21:38.283000+00:00",
    "updated_at": null
  }
]
```

---

### 3. Get Training Session

**Endpoint:** `GET /training-sessions/{session_id}`

**Description:** Get details of a specific training session.

**Path Parameters:**
- `session_id` (required): UUID of the training session

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
  "coach_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Penalty Kicks Drill",
  "session_type": "drill",
  "session_date": "2026-06-08T10:30:00+00:00",
  "notes": "Focused on one-on-one scenarios",
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": null
}
```

**Error Response:**
- `404 Not Found`: If session_id doesn't exist

---

### 4. Update Training Session

**Endpoint:** `PUT /training-sessions/{session_id}`

**Description:** Update an existing training session.

**Path Parameters:**
- `session_id` (required): UUID of the training session

**Request Body (all fields optional):**
```json
{
  "title": "Updated Session Title",
  "session_type": "match_analysis",
  "session_date": "2026-06-08T14:30:00Z",
  "notes": "Updated notes"
}
```

**Response (200 OK):**
Returns updated session object (same format as GET)

**Error Response:**
- `404 Not Found`: If session_id doesn't exist

---

### 5. Delete Training Session

**Endpoint:** `DELETE /training-sessions/{session_id}`

**Description:** Delete a training session (also deletes associated videos and processing jobs).

**Path Parameters:**
- `session_id` (required): UUID of the training session

**Response (204 No Content):** No response body

**Error Response:**
- `404 Not Found`: If session_id doesn't exist

---

## Videos

### 1. Create Video

**Endpoint:** `POST /videos`

**Description:** Create a new video record for a training session.

**Request Body:**
```json
{
  "training_session_id": "550e8400-e29b-41d4-a716-446655440002",
  "filename": "session_recording_2026_06_08.mp4",
  "r2_key": null,
  "duration_seconds": 1234.5,
  "size_bytes": 536870912,
  "upload_status": "pending"
}
```

**Request Fields:**
- `training_session_id` (required): UUID of the training session
- `filename` (required): Original filename of the video
- `r2_key` (optional): Cloudflare R2 key (populated after upload)
- `duration_seconds` (optional): Duration of video in seconds
- `size_bytes` (optional): File size in bytes
- `upload_status` (optional): Upload status ("pending", "uploading", "completed", "failed"). Default: "pending"

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "training_session_id": "550e8400-e29b-41d4-a716-446655440002",
  "filename": "session_recording_2026_06_08.mp4",
  "r2_key": null,
  "duration_seconds": 1234.5,
  "size_bytes": 536870912,
  "upload_status": "pending",
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": null
}
```

**Error Response:**
- `404 Not Found`: If training_session_id doesn't exist
- `422 Unprocessable Entity`: Validation error

---

### 2. List Videos

**Endpoint:** `GET /videos`

**Description:** List all videos with optional filtering.

**Query Parameters:**
- `training_session_id` (optional): Filter videos by training session UUID

**Example Requests:**
```
GET /videos                                               # All videos
GET /videos?training_session_id=550e8400-e29b-...        # Videos for specific session
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "training_session_id": "550e8400-e29b-41d4-a716-446655440002",
    "filename": "session_recording_2026_06_08.mp4",
    "r2_key": null,
    "duration_seconds": 1234.5,
    "size_bytes": 536870912,
    "upload_status": "pending",
    "created_at": "2026-06-08T16:21:38.283000+00:00",
    "updated_at": null
  }
]
```

---

### 3. Get Video

**Endpoint:** `GET /videos/{video_id}`

**Description:** Get details of a specific video.

**Path Parameters:**
- `video_id` (required): UUID of the video

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "training_session_id": "550e8400-e29b-41d4-a716-446655440002",
  "filename": "session_recording_2026_06_08.mp4",
  "r2_key": "training-sessions/2026/06/08/recording.mp4",
  "duration_seconds": 1234.5,
  "size_bytes": 536870912,
  "upload_status": "completed",
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": "2026-06-08T16:22:15.105000+00:00"
}
```

**Error Response:**
- `404 Not Found`: If video_id doesn't exist

---

### 4. Update Video

**Endpoint:** `PUT /videos/{video_id}`

**Description:** Update an existing video record.

**Path Parameters:**
- `video_id` (required): UUID of the video

**Request Body (all fields optional):**
```json
{
  "r2_key": "training-sessions/2026/06/08/recording.mp4",
  "duration_seconds": 1234.5,
  "size_bytes": 536870912,
  "upload_status": "completed"
}
```

**Response (200 OK):**
Returns updated video object

**Error Response:**
- `404 Not Found`: If video_id doesn't exist

---

### 5. Delete Video

**Endpoint:** `DELETE /videos/{video_id}`

**Description:** Delete a video (also deletes associated processing jobs).

**Path Parameters:**
- `video_id` (required): UUID of the video

**Response (204 No Content):** No response body

**Error Response:**
- `404 Not Found`: If video_id doesn't exist

---

## Processing Jobs

### 1. Create Processing Job

**Endpoint:** `POST /processing-jobs`

**Description:** Create a new processing job for a video.

**Request Body:**
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "pending",
  "progress": 0.0,
  "error_message": null
}
```

**Request Fields:**
- `video_id` (required): UUID of the video to process
- `status` (optional): Job status ("pending", "processing", "completed", "failed"). Default: "pending"
- `progress` (optional): Processing progress 0-100. Default: 0.0
- `error_message` (optional): Error details if job failed

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "video_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "pending",
  "progress": 0.0,
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": null
}
```

**Error Response:**
- `404 Not Found`: If video_id doesn't exist
- `422 Unprocessable Entity`: Validation error

---

### 2. List Processing Jobs

**Endpoint:** `GET /processing-jobs`

**Description:** List all processing jobs with optional filtering.

**Query Parameters:**
- `video_id` (optional): Filter jobs by video UUID
- `status` (optional): Filter jobs by status ("pending", "processing", "completed", "failed")

**Example Requests:**
```
GET /processing-jobs                                    # All jobs
GET /processing-jobs?video_id=550e8400-e29b-...        # Jobs for specific video
GET /processing-jobs?status=pending                     # Pending jobs
GET /processing-jobs?video_id=550e8400-e29b-&status=completed  # Completed jobs for video
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440004",
    "video_id": "550e8400-e29b-41d4-a716-446655440003",
    "status": "processing",
    "progress": 45.5,
    "started_at": "2026-06-08T16:22:00.000000+00:00",
    "completed_at": null,
    "error_message": null,
    "created_at": "2026-06-08T16:21:38.283000+00:00",
    "updated_at": "2026-06-08T16:22:30.500000+00:00"
  }
]
```

---

### 3. Get Processing Job

**Endpoint:** `GET /processing-jobs/{job_id}`

**Description:** Get details of a specific processing job.

**Path Parameters:**
- `job_id` (required): UUID of the processing job

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "video_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "completed",
  "progress": 100.0,
  "started_at": "2026-06-08T16:22:00.000000+00:00",
  "completed_at": "2026-06-08T16:34:15.200000+00:00",
  "error_message": null,
  "created_at": "2026-06-08T16:21:38.283000+00:00",
  "updated_at": "2026-06-08T16:34:15.200000+00:00"
}
```

**Error Response:**
- `404 Not Found`: If job_id doesn't exist

---

### 4. Update Processing Job

**Endpoint:** `PUT /processing-jobs/{job_id}`

**Description:** Update an existing processing job (e.g., update progress or mark as completed).

**Path Parameters:**
- `job_id` (required): UUID of the processing job

**Request Body (all fields optional):**
```json
{
  "status": "completed",
  "progress": 100.0,
  "error_message": null
}
```

**Response (200 OK):**
Returns updated job object

**Error Response:**
- `404 Not Found`: If job_id doesn't exist

---

### 5. Delete Processing Job

**Endpoint:** `DELETE /processing-jobs/{job_id}`

**Description:** Delete a processing job record.

**Path Parameters:**
- `job_id` (required): UUID of the processing job

**Response (204 No Content):** No response body

**Error Response:**
- `404 Not Found`: If job_id doesn't exist

---

## Error Response Format

All errors follow this format:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Deletion successful |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server error |

---

## Workflow Example

### Create a Complete Training Session with Video and Processing Job

```bash
# 1. Create training session
curl -X POST http://localhost:8001/api/v1/training-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
    "coach_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Penalty Kicks Drill",
    "session_type": "drill",
    "session_date": "2026-06-08T10:30:00Z",
    "notes": "Focused training"
  }'
# Response includes: session_id = "550e8400-e29b-41d4-a716-446655440002"

# 2. Create video for session
curl -X POST http://localhost:8001/api/v1/videos \
  -H "Content-Type: application/json" \
  -d '{
    "training_session_id": "550e8400-e29b-41d4-a716-446655440002",
    "filename": "recording.mp4",
    "upload_status": "pending"
  }'
# Response includes: video_id = "550e8400-e29b-41d4-a716-446655440003"

# 3. Create processing job for video
curl -X POST http://localhost:8001/api/v1/processing-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "550e8400-e29b-41d4-a716-446655440003",
    "status": "pending"
  }'
# Response includes: job_id = "550e8400-e29b-41d4-a716-446655440004"

# 4. Get processing job status
curl http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004

# 5. Update job progress
curl -X PUT http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processing",
    "progress": 50.0
  }'
```

---

## Rate Limiting

No rate limiting is currently implemented. This will be added in future sprints.

## Authentication

No authentication is currently required. This will be added in future sprints with JWT tokens.

## Pagination

No pagination is currently implemented. List endpoints return all records. This will be added if needed for large datasets.
