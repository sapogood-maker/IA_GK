Goalkeeper AI — API Endpoints (FastAPI)

Auth
- POST /api/v1/auth/signup -> {name,email,password} -> 201 user
- POST /api/v1/auth/login -> {email,password} -> {access_token, refresh_token}
- POST /api/v1/auth/refresh -> {refresh_token} -> new tokens

Users & Roles
- GET /api/v1/users -> [users] (admin)
- GET /api/v1/users/{id}
- PATCH /api/v1/users/{id}

Clubs
- POST /api/v1/clubs -> create club (admin)
- GET /api/v1/clubs -> list
- GET /api/v1/clubs/{id}

Coaches
- POST /api/v1/coaches -> create
- GET /api/v1/coaches/{id}

Goalkeepers
- POST /api/v1/goalkeepers -> create
- GET /api/v1/goalkeepers -> list/filter
- GET /api/v1/goalkeepers/{id}
- PATCH /api/v1/goalkeepers/{id}

Training Sessions
- POST /api/v1/sessions -> create
- GET /api/v1/sessions?goalkeeper_id=...
- GET /api/v1/sessions/{id}

Videos
- POST /api/v1/videos/request-upload -> {session_id, filename, content_type, size} -> {r2_upload_url, r2_key}
- POST /api/v1/videos/confirm-upload -> {r2_key, session_id, duration, width, height, fps}
- GET /api/v1/videos/{id} -> metadata
- POST /api/v1/videos/{id}/enqueue -> enqueue processing job
- GET /api/v1/videos/{id}/download-url -> short-lived signed URL

Processing Jobs / AI Worker
- POST /api/v1/workers/jobs -> (worker API key) {job_id, video_id, r2_url, params} -> 202 (worker accepted)
- POST /api/v1/workers/jobs/{job_id}/progress -> {status, progress, message}
- POST /api/v1/workers/jobs/{job_id}/results -> {events: [...], artifacts: [{key, type}], metrics}
- GET /api/v1/workers/jobs/{job_id} -> job status

Detected Events & Validation
- GET /api/v1/videos/{video_id}/events -> list events (AI-created)
- POST /api/v1/events/{event_id}/validate -> {action: confirm|edit|reject, corrected_payload}
- POST /api/v1/events/batch-validate -> bulk

Reports
- POST /api/v1/reports/generate -> {video_id OR goalkeeper_id, type} -> triggers generation
- GET /api/v1/reports/{id} -> metadata + signed download URL

AI Assistant (Chat)
- POST /api/v1/assistant/chat -> {user_id, question, context_filters} -> {chat_id, response}
- GET /api/v1/assistant/context -> return relevant RAG items

RAG / Search
- GET /api/v1/search?query=...&filters=... -> nearest matches from vector index

WebSockets
- /ws/validation?video_id=... -> send real-time event updates to coach UI

Security notes
- All endpoints require JWT except worker endpoints which use machine API keys + HMAC signature.
- Rate-limit chat endpoints. Use fine-grained RBAC for editing events and reports.

Payload examples
- Detected event sample (POST to /workers/jobs/{job_id}/results):
{
  "events": [
    {
      "timestamp_seconds": 14.22,
      "event_type": "high_catch",
      "category": "technical",
      "confidence": 0.96,
      "metadata": {"bbox": [x,y,w,h], "frame": 10345, "clip_r2_key": "..."}
    }
  ],
  "artifacts": [ {"key":"frames/videoid/10345.jpg","type":"frame"} ],
  "metrics": {"duration_seconds": 123.4, "gpu_ms": 234567}
}
