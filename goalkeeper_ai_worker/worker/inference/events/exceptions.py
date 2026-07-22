"""Exceções da API de Eventos de Cena - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class SceneAnalysisError(WorkerError):
    """Exceção base de qualquer falha na API de Eventos de Cena."""


class SceneAnalysisInitializationError(SceneAnalysisError):
    """Falha ao resolver ou inicializar um SceneAnalyzer (nome desconhecido
    em WORKER_SCENE_ANALYZER)."""


class SceneAnalysisExecutionError(SceneAnalysisError):
    """Falha durante a execução de SceneAnalyzer.analyze()."""
