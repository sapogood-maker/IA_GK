"""Tipos de suporte da infraestrutura de video."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoProperties:
    """Propriedades do video inteiro, lidas uma unica vez na abertura
    (VideoReader.open()) - fps/dimensoes/contagem de frames/duracao reais."""

    fps: float
    width: int
    height: int
    frame_count: int
    duration_seconds: float
