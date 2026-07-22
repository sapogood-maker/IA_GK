"""Exceções da API de Detecção - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class DetectorError(WorkerError):
    """Exceção base de qualquer falha na API de Detecção."""


class DetectorInitializationError(DetectorError):
    """Falha ao resolver ou inicializar um Detector (nome desconhecido em
    WORKER_DETECTOR, modelo/pesos ausentes, framework não instalado)."""


class DetectorExecutionError(DetectorError):
    """Falha durante a execução de Detector.detect()."""
