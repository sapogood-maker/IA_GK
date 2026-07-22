"""Exceções da API de Tracking - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class TrackerError(WorkerError):
    """Exceção base de qualquer falha na API de Tracking."""


class TrackerInitializationError(TrackerError):
    """Falha ao resolver ou inicializar um Tracker (nome desconhecido em
    WORKER_TRACKER, ou falha na inicialização do algoritmo)."""


class TrackerExecutionError(TrackerError):
    """Falha durante a execução de Tracker.track()."""
