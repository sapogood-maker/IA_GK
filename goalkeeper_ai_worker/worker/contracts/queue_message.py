"""Formato do payload publicado pelo backend no stream Redis `processing_jobs`.

Espelha os campos usados em `app/core/queue.py` (`publish_processing_job`),
sem importar nada do backend.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobMessage:
    """Uma mensagem consumida do stream `processing_jobs`."""

    message_id: str
    job_id: str
    video_id: str
