"""Frame: representa um unico frame decodificado do video."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from worker.video.metadata import FrameMetadata


@dataclass(frozen=True)
class Frame:
    """Um frame decodificado - a imagem (array BGR do OpenCV) + seus metadados."""

    image: np.ndarray
    metadata: FrameMetadata
