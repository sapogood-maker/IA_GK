"""PipelineState: representa todo o estado do processamento de um Job.

Cada Stage do Pipeline recebe e devolve esta mesma estrutura - nunca
dezenas de parametros soltos (AI_WORKER_CONSTITUTION.md, Secao 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from worker.contracts.backend_api import JobDetails
from worker.inference.types import InferenceResult


@dataclass
class PipelineState:
    """Estado mutavel de um Job em processamento, passado de Stage em Stage."""

    job_id: str
    video_id: str
    message_id: str
    started_at: datetime
    job: JobDetails | None = None
    workspace_dir: Path | None = None
    download_path: Path | None = None
    artifact_path: Path | None = None
    inference_result: InferenceResult | None = None
    lock_acquired: bool = False
    status: str = "PROCESSING"
    finished_at: datetime | None = None
    errors: list[str] = field(default_factory=list)
