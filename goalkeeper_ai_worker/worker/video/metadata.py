"""FrameMetadata: metadados associados a um frame especifico."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrameMetadata:
    """Posicao do frame dentro do video + propriedades do video de origem
    (denormalizadas aqui para o Frame ser um registro autocontido)."""

    frame_index: int
    timestamp_seconds: float
    position_seconds: float
    fps: float
    width: int
    height: int
    duration_seconds: float
