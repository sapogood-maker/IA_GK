# Sprint 2A Implementation Summary

## Overview

Sprint 2A infrastructure has been successfully implemented with three new core entities:
- **TrainingSession**: Records of goalkeeper training sessions
- **Video**: Video files associated with training sessions
- **ProcessingJob**: Async processing jobs for video analysis

## Database Models

### TrainingSession
```python
- id: UUID [PK]
- goalkeeper_id: UUID [FK → Goalkeepers]
- coach_id: UUID [FK → Coaches, nullable]
- title: String
- session_type: String (e.g., "drill", "match_analysis")
- session_date: DateTime
- notes: String [nullable]
- created_at: DateTime
- updated_at: DateTime
```

**Relationships:**
- `goalkeeper` (1:N) - One goalkeeper can have many training sessions
- `coach` (1:N, optional) - One coach can conduct many training sessions
- `videos` (1:N) - One session can have many videos

### Video
```python
- id: UUID [PK]
- training_session_id: UUID [FK → TrainingSessions]
- filename: String
- r2_key: String [nullable] - Cloudflare R2 key (populated after upload)
- duration_seconds: Float [nullable]
- size_bytes: Integer [nullable]
- upload_status: String (pending/uploading/completed/failed, default: pending)
- created_at: DateTime
- updated_at: DateTime
```

**Relationships:**
- `training_session` (N:1) - Many videos belong to one session
- `processing_jobs` (1:N) - One video can have multiple processing jobs

### ProcessingJob
```python
- id: UUID [PK]
- video_id: UUID [FK → Videos]
- status: String (pending/processing/completed/failed, default: pending)
- progress: Float (0-100, default: 0.0)
- started_at: DateTime [nullable]
- completed_at: DateTime [nullable]
- error_message: String [nullable]
- created_at: DateTime
- updated_at: DateTime
```

**Relationships:**
- `video` (N:1) - Many jobs can process one video (for retries/different processors)

## API Endpoints

### Training Sessions: `/api/v1/training-sessions`

```
POST   /api/v1/training-sessions              - Create new session
GET    /api/v1/training-sessions              - List sessions (filter by goalkeeper_id or coach_id)
GET    /api/v1/training-sessions/{session_id} - Get specific session
PUT    /api/v1/training-sessions/{session_id} - Update session
DELETE /api/v1/training-sessions/{session_id} - Delete session
```

**Request Body (POST/PUT):**
```json
{
  "goalkeeper_id": "uuid",
  "coach_id": "uuid (optional)",
  "title": "string",
  "session_type": "string",
  "session_date": "2026-06-08T10:30:00Z",
  "notes": "string (optional)"
}
```

**Query Parameters (GET list):**
- `goalkeeper_id` (optional): Filter by goalkeeper
- `coach_id` (optional): Filter by coach

### Videos: `/api/v1/videos`

```
POST   /api/v1/videos              - Create new video
GET    /api/v1/videos              - List videos (filter by training_session_id)
GET    /api/v1/videos/{video_id}   - Get specific video
PUT    /api/v1/videos/{video_id}   - Update video
DELETE /api/v1/videos/{video_id}   - Delete video
```

**Request Body (POST/PUT):**
```json
{
  "training_session_id": "uuid",
  "filename": "string",
  "r2_key": "string (optional)",
  "duration_seconds": 123.5,
  "size_bytes": 1048576,
  "upload_status": "pending"
}
```

**Query Parameters (GET list):**
- `training_session_id` (optional): Filter by session

### Processing Jobs: `/api/v1/processing-jobs`

```
POST   /api/v1/processing-jobs              - Create new job
GET    /api/v1/processing-jobs              - List jobs (filter by video_id or status)
GET    /api/v1/processing-jobs/{job_id}     - Get specific job
PUT    /api/v1/processing-jobs/{job_id}     - Update job
DELETE /api/v1/processing-jobs/{job_id}     - Delete job
```

**Request Body (POST/PUT):**
```json
{
  "video_id": "uuid",
  "status": "pending",
  "progress": 0.0,
  "error_message": "string (optional)"
}
```

**Query Parameters (GET list):**
- `video_id` (optional): Filter by video
- `status` (optional): Filter by status (pending, processing, completed, failed)

## Database Schema Changes

### Migration: `002_add_sprint2a_tables.py`

Creates three new tables with proper foreign keys and indexes:

1. **training_sessions**
   - Foreign keys: goalkeeper_id (CASCADE), coach_id (SET NULL)
   - Indexes: goalkeeper_id, coach_id

2. **videos**
   - Foreign key: training_session_id (CASCADE)
   - Index: training_session_id

3. **processing_jobs**
   - Foreign key: video_id (CASCADE)
   - Index: video_id

**Key Design Decisions:**
- Cascading deletes for trainingsessions and videos (clean up child records)
- SET NULL for optional coach reference (preserve sessions if coach is deleted)
- Progress field defaults to 0.0 for new jobs
- Status defaults to "pending" for new jobs
- Upload status defaults to "pending" for new videos

## Files Created/Modified

### New Files
```
app/api/v1/training_sessions.py   - Training session endpoints
app/api/v1/videos.py              - Video endpoints
app/api/v1/processing_jobs.py     - Processing job endpoints
alembic/versions/002_add_sprint2a_tables.py - Database migration
```

### Modified Files
```
app/models/models.py              - Added TrainingSession, Video, ProcessingJob models
app/schemas/schemas.py            - Added Pydantic schemas for all entities
app/repositories/repositories.py  - Added repository classes for CRUD operations
app/main.py                       - Registered new routers
app/api/v1/__init__.py           - Updated imports
backend_fastapi/ER_DIAGRAM.md    - Updated entity relationships
backend_fastapi/requirements.txt  - Updated psycopg dependency
```

### Configuration
```
.env                              - Created environment configuration
```

## Features Implemented

### CRUD Operations
- ✅ Create (POST)
- ✅ Read (GET by ID, GET all with filtering)
- ✅ Update (PUT)
- ✅ Delete (DELETE)

### Relationships
- ✅ Goalkeeper → TrainingSession (1:N)
- ✅ Coach → TrainingSession (1:N, optional)
- ✅ TrainingSession → Video (1:N)
- ✅ Video → ProcessingJob (1:N)

### Validation
- ✅ Foreign key validation on create
- ✅ 404 errors for missing resources
- ✅ Proper HTTP status codes

### Repository Pattern
- ✅ Centralized CRUD logic
- ✅ Async database operations
- ✅ Clean separation of concerns

## Not Implemented (As Per Requirements)

- ❌ Cloudflare R2 integration (for r2_key storage)
- ❌ AI Worker integration (for video processing)
- ❌ Detected Events (Sprint 3+)
- ❌ Coach Corrections (Sprint 3+)
- ❌ Evaluations (Sprint 3+)
- ❌ Reports generation (Sprint 3+)
- ❌ RAG items for semantic search (Sprint 3+)

## Testing

All routes have been verified to load successfully:

```
[OK] Import successful
[OK] Sprint 2A Routes loaded:
  /api/v1/processing-jobs: ['GET']
  /api/v1/processing-jobs: ['POST']
  /api/v1/processing-jobs/{job_id}: ['DELETE']
  /api/v1/processing-jobs/{job_id}: ['GET']
  /api/v1/processing-jobs/{job_id}: ['PUT']
  /api/v1/training-sessions: ['GET']
  /api/v1/training-sessions: ['POST']
  /api/v1/training-sessions/{session_id}: ['DELETE']
  /api/v1/training-sessions/{session_id}: ['GET']
  /api/v1/training-sessions/{session_id}: ['PUT']
  /api/v1/videos: ['GET']
  /api/v1/videos: ['POST']
  /api/v1/videos/{video_id}: ['DELETE']
  /api/v1/videos/{video_id}: ['GET']
  /api/v1/videos/{video_id}: ['PUT']
```

## Next Steps (Sprint 2B+)

1. **Implement Cloudflare R2 Integration**
   - Add R2 client configuration
   - Implement video upload endpoint
   - Update video model with R2 key management

2. **Implement AI Worker Integration**
   - Setup worker communication protocol
   - Add video analysis request/response handlers
   - Implement processing job status updates

3. **Add Tests**
   - Unit tests for repositories
   - Integration tests for endpoints
   - End-to-end tests for complete workflows

4. **Add Error Handling**
   - More specific error messages
   - Logging for debugging
   - Error recovery mechanisms

5. **Implement Sprint 3 Features**
   - Detected Events model
   - Coach Corrections model
   - Evaluations model
   - Reports generation

## Database Connection

The application uses:
- **Driver**: asyncpg (async PostgreSQL driver)
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic

To run migrations:
```bash
cd backend_fastapi
alembic upgrade head
```

## Environment Setup

Required environment variables (in `.env`):
```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
REFRESH_TOKEN_EXPIRATION_DAYS=7
ENV=development
```

## Code Structure

### Repository Pattern
Each entity has a repository class with methods for:
- `create()` - Create new record
- `get_by_id()` - Get by primary key
- `get_by_*()` - Get by foreign keys or attributes
- `get_all()` - Get all records
- `update()` - Update record
- `delete()` - Delete record

### Dependency Injection
Endpoints use FastAPI's `Depends()` to:
- Inject `AsyncSession` from database
- Inject repository instances
- Ensure proper resource cleanup

### Error Handling
All endpoints return:
- 201 Created (POST)
- 200 OK (GET, PUT)
- 204 No Content (DELETE)
- 404 Not Found (missing resources)
- 422 Unprocessable Entity (validation errors)
