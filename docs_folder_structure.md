Goalkeeper AI — Suggested Repository Folder Structure

/ (repo root)
- backend/ (FastAPI service)
  - app/
    - main.py
    - api/
      - v1/
        - auth.py
        - users.py
        - clubs.py
        - coaches.py
        - goalkeepers.py
        - sessions.py
        - videos.py
        - workers.py
        - events.py
        - reports.py
        - assistant.py
    - core/
      - config.py
      - security.py
      - db.py
    - models/ (pydantic + orm models)
    - services/ (video, r2, report, rag)
    - tasks/ (background jobs)
    - workers/ (interfaces for AI worker)
  - Dockerfile
  - requirements.txt
  - alembic/ (migrations)

- ai_worker/ (GPU-hosted worker)
  - worker.py (entry)
  - pipeline/
    - detector.py (GK + ball)
    - tracker.py (tracking)
    - event_classifier.py
    - utils.py
  - models/ (ONNX or PyTorch model wrappers)
  - Dockerfile (for GPU host)
  - requirements.txt

- frontend/ (Flutter app)
  - lib/
    - src/
      - screens/
      - services/ (api_client, websocket)
      - widgets/
  - pubspec.yaml

- ml/ (training & evaluation)
  - experiments/
  - data_pipeline/

- infra/
  - terraform/ (cloudflare r2, dns, workers infra)
  - k8s/ (deployment manifests)

- docs/
  - architecture/ (this content)

- scripts/
  - deploy.sh
  - local_dev_setup.ps1

- .github/workflows/ (CI/CD)

Notes
- Keep ai_worker as separate repo if preferred; however keeping one monorepo simplifies CI for model versioning and reproducible builds.
- Use environment-specific config files for credentials; never commit secrets.
