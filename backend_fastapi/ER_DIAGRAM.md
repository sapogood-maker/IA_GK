# Goalkeeper AI - Database ER Diagram

## Entity Relationships

```
┌─────────────────────────────────┐
│          USERS                  │
├─────────────────────────────────┤
│ id (UUID) [PK]                  │
│ name (String)                   │
│ email (String) [UNIQUE]         │
│ password_hash (String)          │
│ role (String)                   │
│ created_at (DateTime)           │
│ updated_at (DateTime)           │
└─────────────────────────────────┘
         │
         │ 1:1 (user_id)
         │
    ┌────▼─────────────────────────┐
    │       COACHES                 │
    ├───────────────────────────────┤
    │ id (UUID) [PK]                │
    │ user_id (UUID) [FK → USERS]   │
    │ club_id (UUID) [FK → CLUBS]   │
    │ created_at (DateTime)         │
    └───────────────────────────────┘
            │
            │ 1:N (coach_id)
            │
        ┌───▼─────────────────────────────────┐
        │                                     │
        │                          ┌──────────▼───────────────────────┐
        │                          │   TRAINING_SESSIONS             │
        │                          ├─────────────────────────────────┤
        │                          │ id (UUID) [PK]                  │
        │                          │ goalkeeper_id (FK→GOALKEEPERS)  │
        │                          │ coach_id (FK→COACHES) [nullable]│
        │                          │ title (String)                  │
        │                          │ session_type (String)           │
        │                          │ session_date (DateTime)         │
        │                          │ notes (String) [nullable]       │
        │                          │ created_at (DateTime)           │
        │                          │ updated_at (DateTime)           │
        │                          └─────────────────────────────────┘
        │                                    │
        │                                    │ 1:N (training_session_id)
        │                                    │
        │                              ┌─────▼──────────────────────┐
        │                              │      VIDEOS               │
        │                              ├──────────────────────────┤
        │                              │ id (UUID) [PK]           │
        │                              │ training_session_id (FK) │
        │                              │ filename (String)        │
        │                              │ r2_key (String)          │
        │                              │ duration_seconds (Float) │
        │                              │ size_bytes (Integer)     │
        │                              │ upload_status (String)   │
        │                              │ created_at (DateTime)    │
        │                              │ updated_at (DateTime)    │
        │                              └─────────────────────────┘
        │                                    │
        │                                    │ 1:N (video_id)
        │                                    │
        │                              ┌─────▼──────────────────────┐
        │                              │  PROCESSING_JOBS         │
        │                              ├──────────────────────────┤
        │                              │ id (UUID) [PK]           │
        │                              │ video_id (FK)            │
        │                              │ status (String)          │
        │                              │ progress (Float)         │
        │                              │ started_at (DateTime)    │
        │                              │ completed_at (DateTime)  │
        │                              │ error_message (String)   │
        │                              │ created_at (DateTime)    │
        │                              │ updated_at (DateTime)    │
        │                              └──────────────────────────┘


┌─────────────────────────────────┐
│         CLUBS                   │
├─────────────────────────────────┤
│ id (UUID) [PK]                  │
│ name (String)                   │
│ city (String)                   │
│ created_at (DateTime)           │
└─────────────────────────────────┘
        │
        │ 1:N (club_id)
        │
    ┌────▼────────────────────────┐
    │   GOALKEEPERS               │
    ├────────────────────────────┤
    │ id (UUID) [PK]             │
    │ club_id (UUID) [FK→CLUBS]  │
    │ name (String)              │
    │ birth_date (DateTime)      │
    │ dominant_hand (String)     │
    │ height_cm (Integer)        │
    │ weight_kg (Float)          │
    │ created_at (DateTime)      │
    └────────────────────────────┘
            │
            │ 1:N (goalkeeper_id)
            │
        (See TRAINING_SESSIONS above)
```

## Key Relationships

1. **Users → Coaches (1:1)**
   - One user can become a coach

2. **Clubs → Coaches (1:N)**
   - One club can have multiple coaches

3. **Clubs → Goalkeepers (1:N)**
   - One club can have multiple goalkeepers

4. **Goalkeepers → Training Sessions (1:N)**
   - One goalkeeper can have many training sessions

5. **Coaches → Training Sessions (1:N, Optional)**
   - One coach can conduct many training sessions (nullable)

6. **Training Sessions → Videos (1:N)**
   - One training session can have multiple videos

7. **Videos → Processing Jobs (1:N)**
   - One video can have multiple processing jobs (for retries, different processors, etc.)

## Column Details

### TRAINING_SESSIONS
- **session_type**: Type of session (e.g., "drill", "match_analysis", "technical_training")
- **session_date**: Date and time when the session occurred
- **notes**: Optional notes or observations about the session

### VIDEOS
- **filename**: Original filename of the uploaded video
- **r2_key**: Key for the video in Cloudflare R2 (populated after upload)
- **duration_seconds**: Duration of the video in seconds
- **size_bytes**: File size in bytes
- **upload_status**: Status of upload ("pending", "uploading", "completed", "failed")

### PROCESSING_JOBS
- **status**: Current status ("pending", "processing", "completed", "failed")
- **progress**: Processing progress as percentage (0-100)
- **started_at**: When the processing job started
- **completed_at**: When the processing job completed
- **error_message**: Error details if job failed

## Indexing Strategy

- `users.email`: Indexed for fast lookups
- `coaches.user_id`: Indexed for coach lookup by user
- `coaches.club_id`: Indexed for coaches by club
- `goalkeepers.club_id`: Indexed for goalkeepers by club
- `training_sessions.goalkeeper_id`: Indexed for sessions by goalkeeper
- `training_sessions.coach_id`: Indexed for sessions by coach
- `videos.training_session_id`: Indexed for videos by session
- `processing_jobs.video_id`: Indexed for jobs by video

## Future Relationships (Sprint 3+)

- **Detected Events**: AI-detected events in videos
- **Coach Corrections**: Corrections to detected events by coaches
- **Evaluations**: Goalkeeper evaluations and scores
- **Reports**: Generated analysis reports
- **RAG Items**: For semantic search capabilities
