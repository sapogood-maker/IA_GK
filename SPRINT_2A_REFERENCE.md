# Sprint 2A - Quick Reference Card

## 🎯 Three New Entities

### TrainingSession
```
POST   /api/v1/training-sessions
GET    /api/v1/training-sessions?goalkeeper_id=<uuid>
GET    /api/v1/training-sessions/{session_id}
PUT    /api/v1/training-sessions/{session_id}
DELETE /api/v1/training-sessions/{session_id}

Fields:
  goalkeeper_id (required, UUID)
  coach_id (optional, UUID)
  title (required, string)
  session_type (required, string)
  session_date (required, ISO datetime)
  notes (optional, string)
```

### Video
```
POST   /api/v1/videos
GET    /api/v1/videos?training_session_id=<uuid>
GET    /api/v1/videos/{video_id}
PUT    /api/v1/videos/{video_id}
DELETE /api/v1/videos/{video_id}

Fields:
  training_session_id (required, UUID)
  filename (required, string)
  r2_key (optional, string)
  duration_seconds (optional, float)
  size_bytes (optional, integer)
  upload_status (optional, string) [pending|uploading|completed|failed]
```

### ProcessingJob
```
POST   /api/v1/processing-jobs
GET    /api/v1/processing-jobs?video_id=<uuid>&status=<status>
GET    /api/v1/processing-jobs/{job_id}
PUT    /api/v1/processing-jobs/{job_id}
DELETE /api/v1/processing-jobs/{job_id}

Fields:
  video_id (required, UUID)
  status (optional, string) [pending|processing|completed|failed]
  progress (optional, float) [0-100]
  error_message (optional, string)
```

---

## 📂 File Locations

### Code Files
- **Models**: `backend_fastapi/app/models/models.py`
- **Schemas**: `backend_fastapi/app/schemas/schemas.py`
- **Repositories**: `backend_fastapi/app/repositories/repositories.py`
- **API Routes**:
  - `backend_fastapi/app/api/v1/training_sessions.py`
  - `backend_fastapi/app/api/v1/videos.py`
  - `backend_fastapi/app/api/v1/processing_jobs.py`
- **Main App**: `backend_fastapi/app/main.py`

### Database
- **Migration**: `backend_fastapi/alembic/versions/002_add_sprint2a_tables.py`

### Documentation
- **Index**: `C:\Users\P\IA_GK\SPRINT_2A_INDEX.md` (START HERE)
- **Summary**: `C:\Users\P\IA_GK\SPRINT_2A_SUMMARY.md`
- **Quick Start**: `C:\Users\P\IA_GK\SPRINT_2A_QUICK_START.md`
- **Verification**: `C:\Users\P\IA_GK\SPRINT_2A_VERIFICATION.md`
- **API Details**: `C:\Users\P\IA_GK\backend_fastapi\SPRINT_2A_API_ENDPOINTS.md`
- **Schema Details**: `C:\Users\P\IA_GK\backend_fastapi\SPRINT_2A_SCHEMA.md`

---

## 🚀 Quick Start Commands

```bash
# Install dependencies
cd backend_fastapi
pip install -r requirements.txt

# Create .env file
# DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
# JWT_SECRET_KEY=your-secret-key

# Run migration
alembic upgrade head

# Start server
python -m uvicorn app.main:app --reload --port 8001

# Test API
curl http://localhost:8001/api/v1/training-sessions
curl http://localhost:8001/docs  # Interactive docs
```

---

## 📊 Database Tables

### training_sessions
- **PK**: id (UUID)
- **FK**: goalkeeper_id → goalkeepers (CASCADE)
- **FK**: coach_id → coaches (SET NULL)
- **Indexes**: goalkeeper_id, coach_id

### videos
- **PK**: id (UUID)
- **FK**: training_session_id → training_sessions (CASCADE)
- **Index**: training_session_id

### processing_jobs
- **PK**: id (UUID)
- **FK**: video_id → videos (CASCADE)
- **Index**: video_id

---

## ✅ What's Included

✓ Database models with relationships
✓ Pydantic schemas for validation
✓ Repository pattern for data access
✓ Full CRUD endpoints (15 total)
✓ Foreign key validation
✓ Cascade delete rules
✓ Database migration (Alembic)
✓ Comprehensive documentation
✓ Updated ER diagram
✓ All imports and dependencies

---

## ❌ What's NOT Included

✗ Cloudflare R2 integration (Sprint 2B)
✗ AI Worker integration (Sprint 2B)
✗ Video upload functionality (Sprint 2B)
✗ Detected events model (Sprint 3)
✗ Coach corrections (Sprint 3)
✗ Evaluations (Sprint 3)
✗ Report generation (Sprint 3+)

---

## 🔄 Data Relationships

```
Goalkeeper (1) ──────< (N) TrainingSession
Coaches (1) ──────< (N) TrainingSession
TrainingSession (1) ──────< (N) Video
Video (1) ──────< (N) ProcessingJob
```

---

## 🧪 Testing Example

```bash
# Create training session
curl -X POST http://localhost:8001/api/v1/training-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "goalkeeper_id": "550e8400-e29b-41d4-a716-446655440000",
    "coach_id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Penalty Kicks Drill",
    "session_type": "drill",
    "session_date": "2026-06-08T10:30:00Z",
    "notes": "Training session notes"
  }'

# Create video for session
curl -X POST http://localhost:8001/api/v1/videos \
  -H "Content-Type: application/json" \
  -d '{
    "training_session_id": "<session_id>",
    "filename": "recording.mp4",
    "upload_status": "pending"
  }'

# Create processing job
curl -X POST http://localhost:8001/api/v1/processing-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<video_id>",
    "status": "pending"
  }'

# Get job status
curl http://localhost:8001/api/v1/processing-jobs/<job_id>

# Update job
curl -X PUT http://localhost:8001/api/v1/processing-jobs/<job_id> \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processing",
    "progress": 50.0
  }'
```

---

## 📚 HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 204 | No Content - Deletion successful |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable - Validation error |

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection failed | Check PostgreSQL, verify DATABASE_URL |
| Module not found | Run: `pip install -r requirements.txt` |
| Port 8001 in use | Use different port: `--port 8002` |
| Migration error | Check: `alembic current`, `alembic history` |
| Import error | Verify all new files are in correct locations |

---

## 📖 Documentation Index

| Document | Best For |
|----------|----------|
| SPRINT_2A_INDEX.md | Overview & structure |
| SPRINT_2A_SUMMARY.md | Feature completeness |
| SPRINT_2A_QUICK_START.md | Getting started |
| SPRINT_2A_API_ENDPOINTS.md | API details |
| SPRINT_2A_SCHEMA.md | Database design |
| SPRINT_2A_VERIFICATION.md | Verification checklist |

---

## 🎯 Next Steps

1. **Run Migration**
   ```bash
   alembic upgrade head
   ```

2. **Start Server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. **Test Endpoints**
   ```bash
   curl http://localhost:8001/docs
   ```

4. **Review Documentation**
   - See SPRINT_2A_INDEX.md
   - See SPRINT_2A_QUICK_START.md

5. **Implement Tests** (Next task)

6. **Sprint 2B**
   - Add R2 integration
   - Add AI Worker integration
   - Add video upload

---

## 💡 Key Design Patterns

### Repository Pattern
```python
repo = TrainingSessionRepository(db)
session = await repo.create(...)
sessions = await repo.get_by_goalkeeper_id(...)
```

### Dependency Injection
```python
@app.post("/training-sessions")
async def create_session(
    data: TrainingSessionCreate,
    db: AsyncSession = Depends(get_db)
):
```

### Async/Await
```python
async def create(...):
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
```

---

## 📞 Support Resources

- **API Docs**: http://localhost:8001/docs
- **Alternative Docs**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health

---

*Sprint 2A: Database Models & API Design*
*Status: 100% Complete ✓*
*Date: 2026-06-08*
