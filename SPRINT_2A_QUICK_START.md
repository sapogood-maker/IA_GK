# Sprint 2A Quick Start Guide

## Overview

Sprint 2A adds three new entities to the Goalkeeper AI system:
- **TrainingSession**: Records of goalkeeper training activities
- **Video**: Video files from training sessions
- **ProcessingJob**: Async jobs for analyzing videos

## Quick Setup

### 1. Install Dependencies (if not already done)

```bash
cd backend_fastapi
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file or update existing one:

```env
DATABASE_URL=postgresql+asyncpg://goalkeeper_user:goalkeeper_pass@localhost:5433/goalkeeper_ai
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
REFRESH_TOKEN_EXPIRATION_DAYS=7
ENV=development
```

### 3. Run Database Migration

```bash
cd backend_fastapi
alembic upgrade head
```

This creates the three new tables:
- `training_sessions`
- `videos`
- `processing_jobs`

### 4. Start the Server

```bash
cd backend_fastapi
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
```

Server starts at: `http://localhost:8001`

## API Usage Examples

### Example 1: Create and Process a Training Session

```bash
# 1. Create a training session
TRAINER_ID=$(curl -s -X POST http://localhost:8001/api/v1/training-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
    "coach_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Penalty Kicks",
    "session_type": "drill",
    "session_date": "2026-06-08T10:30:00Z",
    "notes": "Penalty kicks drill"
  }' | jq -r '.id')

echo "Created training session: $TRAINER_ID"

# 2. Create a video for the session
VIDEO_ID=$(curl -s -X POST http://localhost:8001/api/v1/videos \
  -H "Content-Type: application/json" \
  -d "{
    \"training_session_id\": \"$TRAINER_ID\",
    \"filename\": \"recording.mp4\",
    \"upload_status\": \"completed\",
    \"duration_seconds\": 1200.0,
    \"size_bytes\": 536870912
  }" | jq -r '.id')

echo "Created video: $VIDEO_ID"

# 3. Create a processing job for the video
JOB_ID=$(curl -s -X POST http://localhost:8001/api/v1/processing-jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"video_id\": \"$VIDEO_ID\",
    \"status\": \"pending\"
  }" | jq -r '.id')

echo "Created processing job: $JOB_ID"

# 4. Check job status
curl -s http://localhost:8001/api/v1/processing-jobs/$JOB_ID | jq .

# 5. Update job to processing
curl -s -X PUT http://localhost:8001/api/v1/processing-jobs/$JOB_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processing",
    "progress": 25.0
  }' | jq .
```

### Example 2: List All Training Sessions

```bash
# Get all training sessions
curl http://localhost:8001/api/v1/training-sessions | jq .

# Get sessions for a specific goalkeeper
GOALKEEPER_ID="550e8400-e29b-41d4-a716-446655440000"
curl "http://localhost:8001/api/v1/training-sessions?goalkeeper_id=$GOALKEEPER_ID" | jq .

# Get sessions by a specific coach
COACH_ID="550e8400-e29b-41d4-a716-446655440001"
curl "http://localhost:8001/api/v1/training-sessions?coach_id=$COACH_ID" | jq .
```

### Example 3: Manage Videos

```bash
# Get all videos
curl http://localhost:8001/api/v1/videos | jq .

# Get videos for a specific session
curl "http://localhost:8001/api/v1/videos?training_session_id=550e8400-e29b-41d4-a716-446655440002" | jq .

# Get specific video details
curl http://localhost:8001/api/v1/videos/550e8400-e29b-41d4-a716-446655440003 | jq .

# Update video (e.g., mark as uploaded)
curl -X PUT http://localhost:8001/api/v1/videos/550e8400-e29b-41d4-a716-446655440003 \
  -H "Content-Type: application/json" \
  -d '{
    "r2_key": "training-sessions/2026/06/08/video.mp4",
    "upload_status": "completed"
  }' | jq .
```

### Example 4: Track Processing Jobs

```bash
# Get all processing jobs
curl http://localhost:8001/api/v1/processing-jobs | jq .

# Get pending jobs
curl "http://localhost:8001/api/v1/processing-jobs?status=pending" | jq .

# Get jobs for a specific video
curl "http://localhost:8001/api/v1/processing-jobs?video_id=550e8400-e29b-41d4-a716-446655440003" | jq .

# Get job details
curl http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004 | jq .

# Update job progress
curl -X PUT http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processing",
    "progress": 50.0
  }' | jq .

# Mark job as completed
curl -X PUT http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "progress": 100.0
  }' | jq .

# Mark job as failed
curl -X PUT http://localhost:8001/api/v1/processing-jobs/550e8400-e29b-41d4-a716-446655440004 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "failed",
    "error_message": "Processing failed due to codec mismatch"
  }' | jq .
```

## Data Flow

```
1. Create TrainingSession
   ↓
2. Create Video for Session
   ↓
3. Upload Video to R2 (Future Sprint 2B)
   ↓
4. Create ProcessingJob for Video
   ↓
5. AI Worker Processes Video (Future Sprint 2B)
   ↓
6. Job Updates Status & Progress
   ↓
7. Detected Events Stored (Future Sprint 3)
```

## Common Tasks

### Task 1: Add a New Training Session

```python
import requests

session_data = {
    "goalkeeper_id": "your-goalkeeper-uuid",
    "coach_id": "your-coach-uuid",  # optional
    "title": "Session Title",
    "session_type": "drill",
    "session_date": "2026-06-08T10:30:00Z",
    "notes": "Session notes"
}

response = requests.post(
    "http://localhost:8001/api/v1/training-sessions",
    json=session_data
)

print(response.json())
```

### Task 2: Upload a Video for a Session

```python
import requests

video_data = {
    "training_session_id": "your-session-uuid",
    "filename": "video.mp4",
    "upload_status": "pending",
    "duration_seconds": 1200.0,
    "size_bytes": 536870912
}

response = requests.post(
    "http://localhost:8001/api/v1/videos",
    json=video_data
)

print(response.json())
```

### Task 3: Start Processing a Video

```python
import requests

job_data = {
    "video_id": "your-video-uuid",
    "status": "pending"
}

response = requests.post(
    "http://localhost:8001/api/v1/processing-jobs",
    json=job_data
)

print(response.json())
```

### Task 4: Check Processing Progress

```python
import requests

job_id = "your-job-uuid"

response = requests.get(
    f"http://localhost:8001/api/v1/processing-jobs/{job_id}"
)

job = response.json()
print(f"Status: {job['status']}")
print(f"Progress: {job['progress']}%")
```

### Task 5: Update Processing Status

```python
import requests

job_id = "your-job-uuid"

update_data = {
    "status": "processing",
    "progress": 45.5
}

response = requests.put(
    f"http://localhost:8001/api/v1/processing-jobs/{job_id}",
    json=update_data
)

print(response.json())
```

## Database Queries

### Raw SQL Examples

```sql
-- Get all training sessions for a goalkeeper
SELECT * FROM training_sessions 
WHERE goalkeeper_id = 'goalkeeper-uuid'
ORDER BY session_date DESC;

-- Get all videos uploaded in the last 7 days
SELECT * FROM videos 
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- Get all pending processing jobs
SELECT * FROM processing_jobs 
WHERE status = 'pending'
ORDER BY created_at ASC;

-- Get videos with their processing status
SELECT v.*, pj.status as job_status, pj.progress
FROM videos v
LEFT JOIN processing_jobs pj ON v.id = pj.video_id
WHERE v.training_session_id = 'session-uuid';

-- Get processing jobs that took more than 1 hour
SELECT * FROM processing_jobs 
WHERE status = 'completed' 
  AND (completed_at - started_at) > INTERVAL '1 hour'
ORDER BY (completed_at - started_at) DESC;
```

## Testing the API

### Using FastAPI's Built-in Docs

Visit `http://localhost:8001/docs` for interactive API documentation (Swagger UI)

Or visit `http://localhost:8001/redoc` for ReDoc documentation

### Using curl

```bash
# Health check
curl http://localhost:8001/health

# API info
curl http://localhost:8001/

# List all training sessions
curl http://localhost:8001/api/v1/training-sessions
```

### Using Python requests

```python
import requests

# Create session
response = requests.post(
    "http://localhost:8001/api/v1/training-sessions",
    json={
        "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Test Session",
        "session_type": "drill",
        "session_date": "2026-06-08T10:30:00Z"
    }
)
print(response.status_code)  # Should be 201
print(response.json())
```

## Troubleshooting

### Database Connection Error

```
ERROR: Could not connect to database
```

**Solution:**
1. Check PostgreSQL is running
2. Verify DATABASE_URL in `.env`
3. Ensure database exists
4. Check credentials

### Migration Error

```
FAILED: alembic upgrade head
```

**Solution:**
```bash
# Check current migration
alembic current

# View migration history
alembic history

# Rollback one version
alembic downgrade -1
```

### Import Error

```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Solution:**
```bash
pip install -r requirements.txt
```

### Server Won't Start

```
Address already in use
```

**Solution:**
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or use different port
python -m uvicorn app.main:app --port 8002
```

## Documentation Files

- `SPRINT_2A_SUMMARY.md` - High-level overview
- `SPRINT_2A_API_ENDPOINTS.md` - Detailed API documentation
- `SPRINT_2A_SCHEMA.md` - Database schema details
- `SPRINT_2A_VERIFICATION.md` - Verification checklist
- `ER_DIAGRAM.md` - Entity relationships

## Next Steps

### Sprint 2B
- Implement Cloudflare R2 integration
- Add video upload endpoints
- Implement AI Worker integration

### Sprint 3
- Add Detected Events model
- Add Coach Corrections model
- Add Evaluations model
- Generate analysis reports

## Support

For issues or questions:
1. Check documentation files
2. Review FastAPI swagger docs at `/docs`
3. Check database logs
4. Review application logs

## Files Modified in Sprint 2A

**New Files:**
- `app/api/v1/training_sessions.py`
- `app/api/v1/videos.py`
- `app/api/v1/processing_jobs.py`
- `alembic/versions/002_add_sprint2a_tables.py`
- `.env` (environment configuration)

**Updated Files:**
- `app/models/models.py`
- `app/schemas/schemas.py`
- `app/repositories/repositories.py`
- `app/main.py`
- `app/api/v1/__init__.py`
- `backend_fastapi/ER_DIAGRAM.md`
- `backend_fastapi/requirements.txt`
