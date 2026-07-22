"""ColorProcessor: converte a imagem de BGR (nativo do OpenCV) para RGB.

Delega a transformação em si a `inference.frame_ops.convert_bgr_to_rgb`
(Sprint W6) - evita duplicar a lógica de conversão de cor entre o
Processor e a função pura já existente."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.frame_ops import convert_bgr_to_rgb
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata


class ColorProcessor(FrameProcessor):
    """Única responsabilidade: normalizar o espaço de cor para RGB."""

    name = "color"

    def __init__(self, settings: WorkerSettings) -> None:
        pass

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.enable_color_processor

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        start = time.monotonic()
        converted = convert_bgr_to_rgb(Frame(image=frame, metadata=metadata))
        context.record(self.name, (time.monotonic() - start) * 1000)
        return converted.image, converted.metadata, context
