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
    │ height_cm (String)         │
    │ weight_kg (String)         │
    │ created_at (DateTime)      │
    └────────────────────────────┘


Future Relationships (Sprint 2+):

┌────────────────────────────┐
│   TRAINING_SESSIONS         │
├────────────────────────────┤
│ id (UUID) [PK]             │
│ goalkeeper_id (FK)         │─────────────────────────┐
│ coach_id (FK)              │                         │
│ title (String)             │                         │
│ session_date (DateTime)    │                         │
│ category (String)          │                         │
└────────────────────────────┘                         │
         │                                              │
         │ 1:N                                          │
         │                                              │
    ┌────▼──────────────────────┐                      │
    │      VIDEOS               │                      │
    ├───────────────────────────┤                      │
    │ id (UUID) [PK]            │                      │
    │ session_id (FK)           │                      │
    │ r2_key (String)           │                      │
    │ duration_seconds (Float)  │                      │
    │ status (String)           │                      │
    └───────────────────────────┘                      │
         │                                              │
         │ 1:N                                          │
         │                                              │
    ┌────▼──────────────────────┐                      │
    │  DETECTED_EVENTS          │                      │
    ├───────────────────────────┤                      │
    │ id (UUID) [PK]            │                      │
    │ video_id (FK)             │                      │
    │ timestamp_seconds (Float) │                      │
    │ event_type (String)       │                      │
    │ confidence (Float)        │                      │
    └───────────────────────────┘                      │
                                                        │
    ┌────────────────────────────┐                     │
    │    COACH_CORRECTIONS       │                     │
    ├────────────────────────────┤                     │
    │ id (UUID) [PK]             │                     │
    │ event_id (FK)              │────┐                │
    │ video_id (FK)              │────┼────────────────┘
    │ coach_id (FK)              │    │
    │ action (String)            │    │
    │ corrected_payload (JSONB)  │    │
    └────────────────────────────┘    │
                                       │
                      ┌────────────────┘
                      │
                ┌─────▼──────────────┐
                │   EVALUATIONS      │
                ├────────────────────┤
                │ id (UUID) [PK]     │
                │ gk_id (FK)         │
                │ coach_id (FK)      │
                │ category (String)  │
                │ score (Float)      │
                │ comments (Text)    │
                └────────────────────┘


┌────────────────────────────┐
│      REPORTS               │
├────────────────────────────┤
│ id (UUID) [PK]             │
│ goalkeeper_id (FK)         │
│ report_type (String)       │
│ r2_key (String)            │
│ generated_at (DateTime)    │
└────────────────────────────┘


┌────────────────────────────┐
│    RAG_ITEMS (for search)  │
├────────────────────────────┤
│ id (UUID) [PK]             │
│ source_type (String)       │
│ source_id (UUID)           │
│ content (Text)             │
│ embedding (Vector)         │
│ created_at (DateTime)      │
└────────────────────────────┘
```

## Key Relationships

1. **Users → Coaches (1:1)**
   - One user can become a coach

2. **Clubs → Coaches (1:N)**
   - One club can have multiple coaches

3. **Clubs → Goalkeepers (1:N)**
   - One club can have multiple goalkeepers

4. **Goalkeepers → Training Sessions → Videos (1:N:N)**
   - One goalkeeper has many sessions with many videos

5. **Videos → Detected Events (1:N)**
   - One video can have many detected events

6. **Detected Events → Coach Corrections (1:N)**
   - Each event can be corrected multiple times (for history)

## Indexing Strategy

- `users.email`: Indexed for fast lookups
- `coaches.user_id`: Indexed for coach lookup by user
- `coaches.club_id`: Indexed for coaches by club
- `goalkeepers.club_id`: Indexed for goalkeepers by club
- `detected_events.video_id, timestamp_seconds`: Composite index for event queries
- `detected_events.event_type`: Indexed for filtering by event type
