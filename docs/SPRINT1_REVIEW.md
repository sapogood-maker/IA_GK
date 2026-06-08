# Sprint 1 Review - Database Schema & API Readiness Assessment

**Review Date**: June 8, 2026  
**Status**: ✅ Sprint 1 Complete & Validated  
**Target**: Architecture validation for future sprints

---

## 1. Current Database Schema

### ER Diagram (Current State)

```
┌──────────────────┐
│      Users       │
├──────────────────┤
│ id (UUID, PK)    │◄─────────────┐
│ name             │              │
│ email (unique)   │              │
│ password_hash    │              │
│ role             │              │ 1:N relationship
│ created_at       │              │
│ updated_at       │              │
└──────────────────┘              │
                                  │
                            ┌─────┴──────────┐
                            │    Coaches     │
                            ├────────────────┤
                            │ id (UUID, PK)  │
                            │ user_id (FK)   │──┐
                            │ club_id (FK)   │  │ (optional)
                            │ created_at     │  │
                            └────────────────┘  │
                                 │              │
                                 │              │
                                 │ (optional)   │
                            ┌────▼─────────┐   │
                            │    Clubs     │   │
                            ├──────────────┤   │
                            │ id (UUID,PK) │◄──┘
                            │ name         │
                            │ city         │
                            │ created_at   │
                            └────┬─────────┘
                                 │
                                 │ 1:N relationship
                                 │
                            ┌────▼──────────────┐
                            │   Goalkeepers     │
                            ├───────────────────┤
                            │ id (UUID, PK)     │
                            │ club_id (FK)      │
                            │ name              │
                            │ birth_date        │
                            │ dominant_hand     │
                            │ height_cm         │
                            │ weight_kg         │
                            │ created_at        │
                            └───────────────────┘
```

### Table Definitions

#### **Users**
- **id**: UUID (Primary Key)
- **name**: String - Goalkeeper/Coach/Admin name
- **email**: String (Unique, Indexed) - Login credential
- **password_hash**: String - Hashed password
- **role**: String - Values: `admin`, `club_admin`, `coach`, `viewer` (default: "viewer")
- **created_at**: DateTime with timezone
- **updated_at**: DateTime with timezone
- **Relationships**: 1:N → Coaches

**Foreign Keys**: None (root entity)

---

#### **Clubs**
- **id**: UUID (Primary Key)
- **name**: String - Club name
- **city**: String (Optional) - Club location
- **created_at**: DateTime with timezone
- **Relationships**: 
  - 1:N → Coaches (optional affiliation)
  - 1:N → Goalkeepers

**Foreign Keys**: None (root entity)

---

#### **Coaches**
- **id**: UUID (Primary Key)
- **user_id**: UUID (Foreign Key → Users.id) - **Cascade Delete**
- **club_id**: UUID (Foreign Key → Clubs.id, Optional) - **Set NULL on Delete**
- **created_at**: DateTime with timezone
- **Relationships**:
  - N:1 → Users (back_populates)
  - N:1 → Clubs (back_populates, optional)

**Foreign Keys**:
- `user_id` → `users.id` (REQUIRED, CASCADE DELETE)
- `club_id` → `clubs.id` (OPTIONAL, SET NULL)

---

#### **Goalkeepers**
- **id**: UUID (Primary Key)
- **club_id**: UUID (Foreign Key → Clubs.id) - **Cascade Delete**
- **name**: String - Goalkeeper name
- **birth_date**: DateTime with timezone (Optional)
- **dominant_hand**: String (Optional) - Values: "left", "right"
- **height_cm**: Integer (Optional) - Height in centimeters
- **weight_kg**: Float (Optional) - Weight in kilograms
- **created_at**: DateTime with timezone
- **Relationships**: N:1 → Clubs (back_populates)

**Foreign Keys**: 
- `club_id` → `clubs.id` (REQUIRED, CASCADE DELETE)

---

## 2. Current API Endpoints (Sprint 1)

### Authentication Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/auth/register` | POST | User registration | ✅ Implemented |
| `/api/v1/auth/login` | POST | User login with JWT | ✅ Implemented |
| `/api/v1/auth/refresh` | POST | Refresh access token | ✅ Implemented |
| `/api/v1/auth/me` | GET | Get current user info | ✅ Implemented |

### User Management Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/users` | GET | List all users | ✅ Implemented |
| `/api/v1/users/{user_id}` | GET | Get user details | ✅ Implemented |

### Club Management Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/clubs` | POST | Create club | ✅ Implemented |
| `/api/v1/clubs` | GET | List all clubs | ✅ Implemented |
| `/api/v1/clubs/{club_id}` | GET | Get club details | ✅ Implemented |

### Coach Management Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/coaches` | POST | Create coach profile | ✅ Implemented |
| `/api/v1/coaches/{coach_id}` | GET | Get coach details | ✅ Implemented |

### Goalkeeper Management Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/goalkeepers` | POST | Create goalkeeper | ✅ Implemented |
| `/api/v1/goalkeepers` | GET | List goalkeepers (filterable by club_id) | ✅ Implemented |
| `/api/v1/goalkeepers/{gk_id}` | GET | Get goalkeeper details | ✅ Implemented |

### System Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/health` | GET | Health check | ✅ Implemented |
| `/` | GET | API info | ✅ Implemented |
| `/docs` | GET | Swagger OpenAPI UI | ✅ Implemented |
| `/openapi.json` | GET | OpenAPI schema | ✅ Implemented |

---

## 3. Data Type Validation

### String Fields (Text)
- ✅ `users.name`
- ✅ `users.email`
- ✅ `users.role`
- ✅ `clubs.name`
- ✅ `clubs.city`
- ✅ `goalkeepers.name`
- ✅ `goalkeepers.dominant_hand`

### DateTime Fields (with timezone)
- ✅ `users.created_at`
- ✅ `users.updated_at`
- ✅ `clubs.created_at`
- ✅ `coaches.created_at`
- ✅ `goalkeepers.birth_date`
- ✅ `goalkeepers.created_at`

### UUID Fields (Primary & Foreign Keys)
- ✅ All `id` columns
- ✅ All FK relationships

### Numeric Fields (CORRECTED in Sprint 1 Review)
- ✅ `goalkeepers.height_cm` - Integer (cm precision)
- ✅ `goalkeepers.weight_kg` - Float (kg with decimals)

---

## 4. Identified Gaps for Goalkeeper AI

### Sprint 2: Video Processing Infrastructure

**Entities to Implement**:

#### **TrainingSession**
```sql
id (UUID, PK)
club_id (UUID, FK → Clubs)
goalkeeper_id (UUID, FK → Goalkeepers)
coach_id (UUID, FK → Coaches, optional)
title (String)
description (Text)
session_date (DateTime)
duration_minutes (Integer)
field_location (String, optional)
weather_conditions (String, optional)
created_at (DateTime)
updated_at (DateTime)
```

**Purpose**: Track training sessions where videos are recorded  
**Relationships**:
- N:1 → Clubs
- N:1 → Goalkeepers
- N:1 → Coaches (optional - who conducted the session)

---

#### **Video**
```sql
id (UUID, PK)
training_session_id (UUID, FK → TrainingSessions)
goalkeeper_id (UUID, FK → Goalkeepers)
filename (String)
s3_key (String) - Cloudflare R2 storage key
duration_seconds (Integer)
file_size_bytes (BigInteger)
fps (Integer, optional)
resolution (String, optional) - "1080p", "720p", etc.
upload_status (String) - "pending", "uploading", "completed", "failed"
upload_progress (Float) - 0-100%
created_at (DateTime)
updated_at (DateTime)
```

**Purpose**: Store video metadata and R2 storage references  
**Relationships**:
- N:1 → TrainingSessions
- N:1 → Goalkeepers
- 1:N → ProcessingJobs
- 1:N → DetectedEvents

---

#### **ProcessingJob**
```sql
id (UUID, PK)
video_id (UUID, FK → Videos)
job_type (String) - "detection", "analysis", "report_generation"
status (String) - "queued", "processing", "completed", "failed"
worker_type (String) - "yolo", "action_classifier", "report_gen"
started_at (DateTime, optional)
completed_at (DateTime, optional)
error_message (Text, optional)
result_metadata (JSON, optional)
created_at (DateTime)
```

**Purpose**: Track AI processing tasks in the AI Worker queue  
**Relationships**:
- N:1 → Videos
- 1:N → DetectedEvents

**Note**: This entity likely needs a distributed message queue (Celery + Redis or RabbitMQ) for job management.

---

#### **DetectedEvent**
```sql
id (UUID, PK)
video_id (UUID, FK → Videos)
processing_job_id (UUID, FK → ProcessingJobs, optional)
event_type (String) - "dive", "save", "kick", "positioning_error", "hand_error"
confidence_score (Float) - 0-1 (AI model confidence)
timestamp_seconds (Float) - Position in video where event occurs
duration_seconds (Float, optional) - Event duration
bounding_box (JSON) - {x, y, width, height} coordinates in frame
frame_number (Integer, optional)
ai_model_version (String) - YOLO version used for detection
created_at (DateTime)
```

**Purpose**: Store detected goalkeeper events from video analysis  
**Relationships**:
- N:1 → Videos
- N:1 → ProcessingJobs (optional)
- 1:N → Evaluations

---

#### **Evaluation**
```sql
id (UUID, PK)
detected_event_id (UUID, FK → DetectedEvents)
evaluator_id (UUID, FK → Users - coach/trainer)
rating (Integer) - 1-5 scale
comments (Text, optional)
evaluation_category (String) - "technique", "positioning", "decision_making", "athleticism"
created_at (DateTime)
updated_at (DateTime)
```

**Purpose**: Store human expert feedback on AI-detected events  
**Relationships**:
- N:1 → DetectedEvents
- N:1 → Users (evaluator)

---

#### **Report**
```sql
id (UUID, PK)
goalkeeper_id (UUID, FK → Goalkeepers)
training_session_id (UUID, FK → TrainingSessions)
report_type (String) - "session_analysis", "skill_assessment", "progress_summary"
title (String)
content (JSON or Text) - Structured report data
key_metrics (JSON) - {event_type: count, ...}
recommendations (Text)
generated_by (UUID, FK → Users, optional - AI system or coach)
created_at (DateTime)
```

**Purpose**: Store generated analysis reports  
**Relationships**:
- N:1 → Goalkeepers
- N:1 → TrainingSessions
- 1:N → ReportSections (optional, for detailed reports)

---

### Architecture Patterns for Sprint 2+

#### **Event Streaming (WebSocket)**
```python
# Future: Real-time updates during video processing
WebSocket: /ws/video/{video_id}/status
- Sends: Job status, progress percentage, detected events as they're found
```

#### **S3/R2 Integration**
```python
# Video storage endpoints needed:
POST /api/v1/videos/{video_id}/upload-url  # Get pre-signed URL
GET /api/v1/videos/{video_id}/download-url # Get download URL
```

#### **Job Queue Pattern**
```python
# Background processing:
- FastAPI endpoint → Redis Queue → AI Worker (port 8002)
- Status tracking via ProcessingJob entity
- WebSocket notifications for real-time updates
```

---

## 5. Database Schema Recommendations

### Add Indexes for Performance

```sql
-- Training Sessions
CREATE INDEX idx_training_sessions_goalkeeper_id ON training_sessions(goalkeeper_id);
CREATE INDEX idx_training_sessions_session_date ON training_sessions(session_date);

-- Videos
CREATE INDEX idx_videos_training_session_id ON videos(training_session_id);
CREATE INDEX idx_videos_upload_status ON videos(upload_status);

-- Processing Jobs
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at);

-- Detected Events
CREATE INDEX idx_detected_events_event_type ON detected_events(event_type);
CREATE INDEX idx_detected_events_confidence ON detected_events(confidence_score);

-- Reports
CREATE INDEX idx_reports_goalkeeper_id ON reports(goalkeeper_id);
CREATE INDEX idx_reports_created_at ON reports(created_at);
```

### Partitioning Strategy (Future)

For large-scale deployments, consider partitioning:
- **Videos** - By `created_at` (monthly partitions)
- **DetectedEvents** - By `video_id` (range partitioning)
- **Reports** - By `created_at` (quarterly partitions)

---

## 6. Sprint 2+ Implementation Roadmap

### Phase 1: Training Sessions & Video Management
- [ ] Create TrainingSession model & API endpoints
- [ ] Create Video model & API endpoints
- [ ] Implement pre-signed URL generation for R2 uploads
- [ ] Add progress tracking for video uploads
- **Timeline**: Sprint 2, Week 1-2

### Phase 2: Video Processing Pipeline
- [ ] Create ProcessingJob model
- [ ] Implement Redis/Celery job queue
- [ ] Create AI Worker (port 8002) with YOLO integration
- [ ] WebSocket support for real-time status updates
- **Timeline**: Sprint 2, Week 2-3

### Phase 3: Event Detection & Analysis
- [ ] Create DetectedEvent model & API
- [ ] Integrate YOLO goalkeeper detection model
- [ ] Create Evaluation model for human feedback
- [ ] Build event filtering & search APIs
- **Timeline**: Sprint 3, Week 1-2

### Phase 4: Reports & Insights
- [ ] Create Report model & generation system
- [ ] Build report templates (session summary, skill assessment)
- [ ] Add metrics aggregation & trending
- [ ] Generate PDF/Excel exports
- **Timeline**: Sprint 3, Week 2-3

### Phase 5: AI Assistant (RAG)
- [ ] Integrate LLM for goalkeeper coaching insights
- [ ] Build RAG system with detected events as context
- [ ] Create AI-powered recommendations engine
- [ ] Add chat/conversation endpoints
- **Timeline**: Sprint 4

---

## 7. Configuration & Port Summary

### Current Setup (Sprint 1)
| Service | Port | Status | Notes |
|---------|------|--------|-------|
| FastAPI Backend | **8001** | ✅ Active | REST API + OpenAPI |
| PostgreSQL | **5433** | ✅ Active | Local dev (mapped from 5432) |
| AI Worker | **8002** | 🔜 Reserved | Sprint 2+ (GPU support) |
| Frontend (Flutter) | 5000 | 🔜 Planned | Web/Mobile UI |

### Environment Variables
```bash
DATABASE_URL=postgresql://goalkeeper_user:goalkeeper_pass@localhost:5433/goalkeeper_ai
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
REFRESH_TOKEN_EXPIRATION_DAYS=7
ENV=development

# Future (Sprint 2+):
# R2_BUCKET_NAME=goalkeeper-ai-videos
# R2_ENDPOINT=https://xxxxx.r2.cloudflarestorage.com
# R2_ACCESS_KEY_ID=...
# R2_SECRET_ACCESS_KEY=...
# REDIS_URL=redis://localhost:6379/0
# AI_WORKER_URL=http://localhost:8002
```

---

## 8. Migration & Upgrade Path

### From Sprint 1 to Sprint 2

**Step 1**: Add new tables to migration
```python
# alembic/versions/002_add_sprint2_entities.py
def upgrade():
    # Create training_sessions, videos, processing_jobs tables
```

**Step 2**: Update relationships in models
```python
# app/models/models.py
# Add new models maintaining referential integrity
```

**Step 3**: Deploy with blue-green strategy
```bash
# Keep Sprint 1 running while deploying Sprint 2 schema
# Once tested, switch traffic to new deployment
```

---

## 9. Validation Checklist

✅ **Port Configuration**
- [x] Backend API: Port 8001
- [x] PostgreSQL: Port 5433 (local)
- [x] AI Worker: Port 8002 reserved

✅ **Data Types**
- [x] UUID for all IDs
- [x] height_cm as Integer
- [x] weight_kg as Float
- [x] DateTime with timezone for all timestamps

✅ **Relationships**
- [x] User → Coaches (1:N)
- [x] Club → Coaches (1:N, optional)
- [x] Club → Goalkeepers (1:N)
- [x] Foreign keys with cascade/set-null policies

✅ **API Coverage**
- [x] Authentication (4 endpoints)
- [x] Users (2 endpoints)
- [x] Clubs (3 endpoints)
- [x] Coaches (2 endpoints)
- [x] Goalkeepers (3 endpoints)
- [x] System endpoints (4 endpoints)

✅ **Documentation**
- [x] API endpoints documented
- [x] Database schema defined
- [x] Setup instructions provided
- [x] Environment variables documented

---

## 10. Next Steps

1. **Sprint 2 Planning**
   - Finalize TrainingSession and Video schema
   - Design AI Worker communication protocol
   - Plan WebSocket implementation

2. **Infrastructure Preparation**
   - Set up Cloudflare R2 bucket
   - Configure Redis/message queue
   - Prepare GPU worker environment

3. **Testing**
   - Unit tests for CRUD operations
   - Integration tests for API endpoints
   - Load testing for video upload/processing

---

**Approved by**: Sprint Review Team  
**Last Updated**: June 8, 2026  
**Next Review**: Before Sprint 2 Implementation
