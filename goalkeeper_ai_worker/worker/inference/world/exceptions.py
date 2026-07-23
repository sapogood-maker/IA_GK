"""Exceções do World Model - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class WorldModelError(WorkerError):
    """Exceção base de qualquer falha no World Model."""


class WorldModelInitializationError(WorldModelError):
    """Falha ao resolver ou inicializar um WorldModel (nome desconhecido
    em WORKER_WORLD_MODEL)."""


class WorldModelExecutionError(WorldModelError):
    """Falha durante a execução de WorldModel.update()."""
