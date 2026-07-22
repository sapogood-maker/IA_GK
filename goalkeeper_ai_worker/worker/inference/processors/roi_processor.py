"""ROIProcessor: recorta a imagem para a Region of Interest configurada.

Delega a transformação em si a `inference.frame_ops.apply_roi` (Sprint
W6) - evita duplicar a lógica de recorte entre o Processor e a função
pura já existente."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.frame_ops import apply_roi
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.inference.types import RegionOfInterest
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata


class ROIProcessor(FrameProcessor):
    """Única responsabilidade: recortar a imagem para a ROI configurada."""

    name = "roi"

    def __init__(self, settings: WorkerSettings) -> None:
        self._roi = RegionOfInterest(
            x=settings.roi_x, y=settings.roi_y, width=settings.roi_width, height=settings.roi_height
        )

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.enable_roi

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        start = time.monotonic()
        cropped = apply_roi(Frame(image=frame, metadata=metadata), self._roi)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return cropped.image, cropped.metadata, context
