# Sprint 2A Database Schema Documentation

## Overview

This document provides detailed information about the database schema changes introduced in Sprint 2A, including table definitions, relationships, and indexing strategy.

## Migration File

**Location:** `alembic/versions/002_add_sprint2a_tables.py`

**Revision:** 002
**Down Revision:** 001

---

## Table: training_sessions

### Purpose
Stores information about goalkeeper training sessions conducted by coaches.

### Schema

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | UUID | PRIMARY KEY | uuid4 | Unique identifier |
| goalkeeper_id | UUID | FOREIGN KEY (goalkeepers.id) ON DELETE CASCADE | NOT NULL | Required reference to goalkeeper |
| coach_id | UUID | FOREIGN KEY (coaches.id) ON DELETE SET NULL | NULL | Optional reference to coach |
| title | String | NOT NULL | - | Session name/title |
| session_type | String | NOT NULL | - | Type: drill, match_analysis, etc. |
| session_date | DateTime (TZ) | NOT NULL | - | When the session occurred |
| notes | String | NULL | - | Optional session notes |
| created_at | DateTime (TZ) | - | CURRENT_TIMESTAMP | Record creation time |
| updated_at | DateTime (TZ) | - | NULL | Last modification time |

### Indexes

```sql
CREATE INDEX ix_training_sessions_goalkeeper_id ON training_sessions(goalkeeper_id);
CREATE INDEX ix_training_sessions_coach_id ON training_sessions(coach_id);
```

### Foreign Keys

```sql
FOREIGN KEY (goalkeeper_id) REFERENCES goalkeepers(id) ON DELETE CASCADE
FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE SET NULL
```

### Relationships

```
Goalkeepers (1) ──────< (N) TrainingSessions
Coaches (1) ──────< (N) TrainingSessions
```

### Cascading Behavior

- **ON DELETE CASCADE (goalkeeper)**: When a goalkeeper is deleted, all their training sessions are deleted
- **ON DELETE SET NULL (coach)**: When a coach is deleted, their training sessions remain but coach_id becomes NULL

### Example Data

```sql
INSERT INTO training_sessions 
(id, goalkeeper_id, coach_id, title, session_type, session_date, notes)
VALUES
(
  '550e8400-e29b-41d4-a716-446655440002',
  '550e8400-e29b-41d4-a716-446655440000',
  '550e8400-e29b-41d4-a716-446655440001',
  'Penalty Kicks Drill',
  'drill',
  '2026-06-08 10:30:00+00:00',
  'Focused on one-on-one scenarios'
);
```

---

## Table: videos

### Purpose
Stores metadata about video recordings of training sessions.

### Schema

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | UUID | PRIMARY KEY | uuid4 | Unique identifier |
| training_session_id | UUID | FOREIGN KEY (training_sessions.id) ON DELETE CASCADE | NOT NULL | Required reference to session |
| filename | String | NOT NULL | - | Original filename |
| r2_key | String | NULL | - | Cloudflare R2 storage key |
| duration_seconds | Float | NULL | - | Video duration in seconds |
| size_bytes | Integer | NULL | - | File size in bytes |
| upload_status | String | NOT NULL | 'pending' | Status: pending, uploading, completed, failed |
| created_at | DateTime (TZ) | - | CURRENT_TIMESTAMP | Record creation time |
| updated_at | DateTime (TZ) | - | NULL | Last modification time |

### Indexes

```sql
CREATE INDEX ix_videos_training_session_id ON videos(training_session_id);
```

### Foreign Keys

```sql
FOREIGN KEY (training_session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
```

### Relationships

```
TrainingSessions (1) ──────< (N) Videos
```

### Upload Status Values

- **pending**: Video created but not yet uploaded
- **uploading**: Video upload in progress
- **completed**: Video successfully uploaded to R2
- **failed**: Video upload failed

### Cascading Behavior

- **ON DELETE CASCADE**: When a training session is deleted, all its videos are deleted

### Example Data

```sql
INSERT INTO videos 
(id, training_session_id, filename, r2_key, duration_seconds, size_bytes, upload_status)
VALUES
(
  '550e8400-e29b-41d4-a716-446655440003',
  '550e8400-e29b-41d4-a716-446655440002',
  'session_recording_2026_06_08.mp4',
  NULL,
  1234.5,
  536870912,
  'pending'
);
```

---

## Table: processing_jobs

### Purpose
Tracks asynchronous video processing jobs for AI analysis and event detection.

### Schema

| Column | Type | Constraints | Default | Notes |
|--------|------|-------------|---------|-------|
| id | UUID | PRIMARY KEY | uuid4 | Unique identifier |
| video_id | UUID | FOREIGN KEY (videos.id) ON DELETE CASCADE | NOT NULL | Required reference to video |
| status | String | NOT NULL | 'pending' | Job status |
| progress | Float | NULL | 0.0 | Progress percentage (0-100) |
| started_at | DateTime (TZ) | NULL | - | When job processing started |
| completed_at | DateTime (TZ) | NULL | - | When job processing completed |
| error_message | String | NULL | - | Error details if failed |
| created_at | DateTime (TZ) | - | CURRENT_TIMESTAMP | Record creation time |
| updated_at | DateTime (TZ) | - | NULL | Last modification time |

### Indexes

```sql
CREATE INDEX ix_processing_jobs_video_id ON processing_jobs(video_id);
```

### Foreign Keys

```sql
FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
```

### Relationships

```
Videos (1) ──────< (N) ProcessingJobs
```

### Job Status Values

- **pending**: Job created but not yet started
- **processing**: Job is currently being processed
- **completed**: Job completed successfully
- **failed**: Job failed with error

### Progress Field

- Range: 0.0 to 100.0
- Updated during processing to show progress
- 0.0 for new jobs
- 100.0 when completed

### Cascading Behavior

- **ON DELETE CASCADE**: When a video is deleted, all its processing jobs are deleted

### Example Data

```sql
INSERT INTO processing_jobs 
(id, video_id, status, progress, started_at, completed_at, error_message)
VALUES
(
  '550e8400-e29b-41d4-a716-446655440004',
  '550e8400-e29b-41d4-a716-446655440003',
  'processing',
  45.5,
  '2026-06-08 16:22:00+00:00',
  NULL,
  NULL
);
```

---

## Entity Relationship Diagram

### Current (Sprint 2A)

```
Users (1) ─────────< (N) Coaches
                       |
                       |
Clubs (1) ────────< (N) Coaches
   |
   |
   +──(1)────────< (N) Goalkeepers
                      |
                      |
                      +──(1)────────< (N) TrainingSessions
                                           |
                                           |─── coach (N:1, optional)
                                           |
                                           +──(1)────────< (N) Videos
                                                              |
                                                              |
                                                              +──(1)────────< (N) ProcessingJobs
```

### Constraints Summary

| Relationship | Type | Delete Rule | Notes |
|-------------|------|-------------|-------|
| Goalkeeper → TrainingSession | 1:N | CASCADE | Remove sessions when GK deleted |
| Coach → TrainingSession | 1:N | SET NULL | Keep sessions when coach deleted |
| TrainingSession → Video | 1:N | CASCADE | Remove videos when session deleted |
| Video → ProcessingJob | 1:N | CASCADE | Remove jobs when video deleted |

---

## Query Patterns

### Common Queries

#### Get all training sessions for a goalkeeper
```sql
SELECT * FROM training_sessions 
WHERE goalkeeper_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY session_date DESC;
```

#### Get all videos for a training session with their processing jobs
```sql
SELECT v.*, pj.*
FROM videos v
LEFT JOIN processing_jobs pj ON v.id = pj.video_id
WHERE v.training_session_id = '550e8400-e29b-41d4-a716-446655440002'
ORDER BY v.created_at DESC;
```

#### Get pending processing jobs
```sql
SELECT * FROM processing_jobs 
WHERE status = 'pending'
ORDER BY created_at ASC;
```

#### Get completed processing jobs with video details
```sql
SELECT pj.*, v.filename, v.duration_seconds, ts.title
FROM processing_jobs pj
JOIN videos v ON pj.video_id = v.id
JOIN training_sessions ts ON v.training_session_id = ts.id
WHERE pj.status = 'completed'
ORDER BY pj.completed_at DESC;
```

#### Get sessions by date range
```sql
SELECT * FROM training_sessions
WHERE session_date BETWEEN '2026-06-01' AND '2026-06-30'
ORDER BY session_date DESC;
```

#### Get all videos for a goalkeeper (through training sessions)
```sql
SELECT v.*, ts.title, ts.session_date
FROM videos v
JOIN training_sessions ts ON v.training_session_id = ts.id
WHERE ts.goalkeeper_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY ts.session_date DESC;
```

---

## Backup and Recovery Considerations

### Cascade Deletes
The CASCADE delete rules mean that:
- Deleting a goalkeeper deletes all their training sessions, videos, and processing jobs
- Deleting a training session deletes all its videos and processing jobs
- Deleting a video deletes all its processing jobs

**Recommendation:** Implement soft deletes (is_deleted flag) if recovery is needed, or use database backups.

### Processing Jobs
Processing jobs should be:
- Archived after 30 days of completion
- Soft deleted instead of hard deleted for audit trail
- Stored with complete error messages for debugging

---

## Performance Optimization

### Index Strategy

Current indexes focus on:
1. **Foreign key lookups** (goalkeeper_id, coach_id, training_session_id, video_id)
2. **Common filters** (session_date, upload_status, job status)

### Future Optimization Options

- **Composite index** on `(goalkeeper_id, session_date DESC)` for fast GK session listing
- **Partial index** on `processing_jobs (status)` where `status != 'completed'` for pending jobs
- **Full-text search** on `title` and `notes` for session search
- **Partitioning** by date if table grows large

---

## Data Integrity

### Constraints Enforced

1. **Foreign Key Integrity**: Database enforces referential integrity
2. **Not Null Constraints**: Required fields are enforced at DB level
3. **Default Values**: Automatically applied on insert
4. **Unique IDs**: UUID primary keys ensure uniqueness

### Application-Level Validation

The API layer adds additional validation:
- UUID format validation
- DateTime format validation
- String length limits
- Enum validation for status fields

---

## Migration Process

### Running the Migration

```bash
# From the backend_fastapi directory
alembic upgrade 002
```

### Rollback

```bash
alembic downgrade 001
```

### Checking Current Version

```bash
alembic current
```

### Seeing Available Migrations

```bash
alembic history
```

---

## Future Schema Enhancements (Sprint 3+)

### Detected Events Table
```sql
CREATE TABLE detected_events (
  id UUID PRIMARY KEY,
  video_id UUID FOREIGN KEY,
  timestamp_seconds FLOAT,
  event_type STRING,
  confidence FLOAT,
  metadata JSONB
)
```

### Coach Corrections Table
```sql
CREATE TABLE coach_corrections (
  id UUID PRIMARY KEY,
  event_id UUID FOREIGN KEY,
  coach_id UUID FOREIGN KEY,
  correction_type STRING,
  payload JSONB
)
```

### Evaluations Table
```sql
CREATE TABLE evaluations (
  id UUID PRIMARY KEY,
  goalkeeper_id UUID FOREIGN KEY,
  coach_id UUID FOREIGN KEY,
  category STRING,
  score FLOAT,
  comments TEXT
)
```

---

## Database Connection Requirements

### Async Driver
- Must use `asyncpg` for async PostgreSQL access
- Connection string format: `postgresql+asyncpg://user:password@host:port/database`

### Transaction Management
- Uses SQLAlchemy 2.0 async session factory
- Each request gets a fresh async session
- Transactions committed automatically after successful operations

### Connection Pooling
- Configured in `app/db/base.py`
- Default pool settings used (pool_size=10, max_overflow=20)
- Can be tuned based on load requirements
