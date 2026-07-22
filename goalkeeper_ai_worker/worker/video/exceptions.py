"""Excecoes da infraestrutura de leitura de video - todas derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError


class VideoError(WorkerError):
    """Excecao base de qualquer falha na leitura de video."""


class VideoOpenError(VideoError):
    """Falha ao abrir o arquivo de video (nao existe ou formato ilegivel)."""


class InvalidVideoError(VideoError):
    """O arquivo abriu, mas nao e um video valido (metadados ilegiveis/zerados)."""


class FrameReadError(VideoError):
    """Falha ao ler um frame especifico durante a iteracao."""
