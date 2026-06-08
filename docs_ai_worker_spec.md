AI Worker — Spec and API

Purpose

Dedicated GPU-hosted service responsible for heavy CV and ML tasks: detection, tracking, event classification, artifact extraction, and uploading results to backend. Must never access Postgres directly; communication exclusively via backend REST API.

Deployment

- Runs on dedicated machine with GPU (user suggested AMD RX 6800 / RX 7900 XTX). Validate driver/stack (ROCm support) early.
- Containerized with GPU access (Docker + ROCm or alternative). If AMD GPU issues arise, use cloud NVIDIA GPU instances or ONNX runtime CPU fallback.

Pipeline stages

1. Preprocessing
  - Download video via R2 signed URL
  - Extract metadata (fps, resolution)
  - Optional stabilization and color normalization

2. Detection
  - Goalkeeper detection (YOLO-family or custom detector)
  - Ball detection
  - Player detection for context

3. Tracking
  - Multi-object tracker (DeepSORT or ByteTrack)
  - Persistent GK identity across frames using jersey color and appearance embedding

4. Event segmentation
  - Sliding-window temporal classification + rule-based heuristics
  - Use per-frame features + tracks to detect events (dives, catches, saves, distribution types)

5. Classification & scoring
  - Confidence scores per event
  - Additional metadata: bbox, representative frame, clip timestamps, heatmaps

6. Artifact generation
  - Thumbnails, keyframe images, short clips for each event
  - Optional pose estimation outputs for technical scoring

7. Upload results
  - POST /api/v1/workers/jobs/{job_id}/results with events, artifacts, metrics
  - Backend returns 200 and persists

Worker API (backend)

- Authentication: X-Worker-Api-Key header and HMAC signature on payload
- Endpoints used:
  - GET job details: /api/v1/workers/jobs/{job_id}
  - POST progress: /api/v1/workers/jobs/{job_id}/progress
  - POST results: /api/v1/workers/jobs/{job_id}/results

Event JSON schema (example)
{
  "timestamp_seconds": 14.22,
  "event_type": "high_catch",
  "category": "technical",
  "confidence": 0.96,
  "metadata": {
    "bbox": [x,y,w,h],
    "frame": 10345,
    "clip_start": 13.5,
    "clip_end": 15.7,
    "goalkeeper_track_id": "trk-abc",
    "assist_player": null
  }
}

Security & Reliability

- Use retries with exponential backoff for uploads and job status updates.
- Upload artifacts to R2 using signed URLs obtained from backend to avoid direct credential storage.
- Limit resource usage per job; implement timeouts and graceful cancellation.

Model lifecycle

- Version models and store model metadata in R2 or a model registry.
- Store training-ready datasets of corrected events and coach_corrections in ML folder (with consent metadata).

Notes on AMD GPUs

- AMD GPUs may require ROCm; test model runtimes early. For portability, prefer ONNX runtime with hardware acceleration where possible. Maintain a CPU fallback to ensure processing completes even without GPU.

