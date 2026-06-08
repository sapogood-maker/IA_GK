Goalkeeper AI — Implementation Roadmap

Phases & Milestones

Phase 1: Core platform & video pipeline (8-12 weeks)
- Sprint 1 (2w): Project setup, infra skeleton, auth, user/club/coach CRUD, DB schema, CI.
- Sprint 2 (2w): Video upload flow (pre-signed R2), video metadata, processing job enqueue, frontend upload UI.
- Sprint 3 (3w): AI Worker minimal pipeline: goalkeeper detection + tracking (produce sample events), worker API integration, end-to-end job run.
- Sprint 4 (2w): Event ingestion, coach validation UI (confirm/edit/reject), store corrections.
- Deliverable: Coaches can upload videos and get auto-detected events to validate.

Phase 2: Event classification, reports, AI assistant (8-10 weeks)
- Implement full event taxonomy (technical/tactical/distribution/match).
- Build report generator (HTML -> PDF with embedded clips & frames).
- Integrate RAG: embeddings for events and reports; vector DB choice (pgvector or Weaviate).
- Build assistant chat with retrieval + LLM (hosted or API). Implement RBAC and usage quotas.

Phase 3: Modeling improvements & production hardening (8-12 weeks)
- Improve CV models (fine-tune detectors, action classifiers), add multi-camera support.
- Build training pipeline to consume coach corrections and retrain models.
- Add advanced features: goalkeeper similarity, talent scouting engine, automated scoring & recommendations.

Cross-cutting tasks
- Monitoring, alerting, SLOs, error reporting
- End-to-end tests and data validation
- Compliance & privacy (consent flows)

Testing & Validation
- Unit tests for backend and worker components
- Integration tests for upload -> worker -> events -> validation
- CV evaluation pipeline (precision/recall per event type)

CI/CD
- Build & push Docker images on merge to main
- Automated migration on deploy (alembic)
- Deploy backend to managed service (k8s or App Service), AI Worker to dedicated GPU node (bare-metal or cloud VM)

Acceptance criteria (Phase 1)
- 90% of uploads processed without manual intervention
- Coach can validate events in UI
- Events persisted with metadata and coach corrections tracked

Estimated team & timeline
- Small core team (1 backend, 1 frontend, 1 ML/worker engineer, 1 devops) -> Phase1: ~10 weeks.

Risks & mitigations
- GPU compatibility (AMD RX series): validate ML stack early; fallback to CPU/ONNX if needed.
- Video variability: create robust preprocessing and labeling pipeline; capture coach-provided context (jersey colors) to boost detection accuracy.

Next actions
- Start Sprint 1: scaffold backend + DB + auth and create CI pipeline. Create initial endpoints and upload flow.
