"""Excecoes da camada de inferencia - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class InferenceError(WorkerError):
    """Excecao base de qualquer falha na camada de inferencia."""


class EngineInitializationError(InferenceError):
    """Falha ao resolver ou inicializar um InferenceEngine (ex.: nome
    desconhecido em WORKER_INFERENCE_ENGINE)."""


class InferenceExecutionError(InferenceError):
    """Falha durante a execucao de InferenceEngine.process()."""
