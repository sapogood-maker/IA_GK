"""Exceções da Analyzer API - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class AnalyzerError(WorkerError):
    """Exceção base de qualquer falha num Analyzer."""


class AnalyzerInitializationError(AnalyzerError):
    """Falha ao resolver ou inicializar um Analyzer (nome desconhecido em
    WORKER_ANALYZERS, ou falha no próprio construtor)."""


class AnalyzerExecutionError(AnalyzerError):
    """Falha durante a execução de Analyzer.analyze()."""
