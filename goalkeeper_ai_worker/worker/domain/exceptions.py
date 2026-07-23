"""Exceções do Football Domain Model - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class FootballDomainError(WorkerError):
    """Exceção base de qualquer falha no Football Domain Model."""


class FootballWorldBuildError(FootballDomainError):
    """Falha ao construir um FootballWorld a partir de um WorldState."""
