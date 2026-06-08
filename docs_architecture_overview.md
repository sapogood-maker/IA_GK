Goalkeeper AI — System Architecture Overview

Summary

Goalkeeper AI is a production-grade platform for futsal goalkeeper scouting, training analysis, performance evaluation, and AI-assisted coaching. Core goals: automated video analysis, event detection, coach validation, RAG-powered assistant, and data accumulation for model training. Frontend: Flutter (web, Android, iOS). Backend: FastAPI. Storage: Cloudflare R2. DB: PostgreSQL. AI Worker: dedicated GPU machine, communicates over secure REST APIs.

High-level components

- Frontend (Flutter): Authentication, Dashboard, Goalkeepers, Clubs, Coaches, Sessions, Video Upload, Reports, AI Assistant Chat, Settings. Uses API gateway + JWT.
- Backend (FastAPI): Auth, User/Club/Coach/Goalkeeper management, Video management, Job orchestration, R2 signed URL generation, Reports, Search & RAG index ingestion, WebSocket/event streaming for coach validation UI.
- AI Worker (separate service on GPU host): Receives processing jobs, downloads video from R2, runs CV/ML pipeline (detection, tracking, event classification), uploads artifacts (frames, thumbnails), posts detected events to backend via secure API, provides progress webhooks.
- Storage: Cloudflare R2 for all binary artifacts (original videos, processed clips, frames, models artifacts, PDF reports). PostgreSQL stores metadata and event records only.
- RAG/Vector DB: Milvus/Weaviate or pgvector hosted alongside Postgres for retrieval (store embeddings for events, reports, transcripts).
- CI/CD & Infra: Docker images, GitHub Actions, Terraform for R2 and infra (Cloudflare), Kubernetes or managed host for backend, separate host for AI Worker (not in Coolify). Monitoring: Prometheus, Grafana, Sentry.

Security and Ops

- Auth: JWT access tokens + refresh tokens; roles (admin, club_admin, coach, viewer). OAuth2 optional for SSO.
- AI Worker auth: machine-scoped API key + HMAC-signed job payloads; token rotation and least-privilege API keys.
- Transport: TLS everywhere. R2 signed URLs for direct upload/download.
- Data privacy: coach corrections and PII protected; audits and consent for data usage in model training.

Data flow (upload -> report)

1. Coach uploads video via frontend using pre-signed R2 URL from backend.
2. Backend stores video object metadata and creates processing_job (status: queued).
3. AI Worker polls backend or receives push webhook with job id and R2 URL (short-lived signed URL).
4. Worker downloads video, runs pipeline: GK detection -> ball detection -> tracking -> temporal segmentation -> event classification -> compile artifacts.
5. Worker uploads event JSON and artifacts to backend via secure API. Backend validates and persists events and artifacts in Postgres and R2.
6. Backend triggers report generation (PDF) and updates RAG indices with embeddings for events and reports.
7. Coach reviews events in UI (confirm/edit/reject). Corrections stored to coach_corrections table and flagged for model training.

Observability

- Worker job metrics (latency, memory, GPU utilization) exported via Prometheus pushgateway.
- Backend metrics (requests, latencies, error rates).
- Logs aggregated to ELK or Loki. Alerts for failed jobs and high error rates.

Next steps

- Provide full DB schema, API endpoints, folder structure, and phase-by-phase implementation roadmap in separate files (created).