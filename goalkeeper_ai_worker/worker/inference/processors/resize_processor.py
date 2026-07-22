"""ResizeProcessor: redimensiona a imagem para as dimensões configuradas.

Delega a transformação em si a `inference.frame_ops.resize_frame`
(Sprint W6) - evita duplicar a lógica de redimensionamento entre o
Processor e a função pura já existente."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.frame_ops import resize_frame
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata


class ResizeProcessor(FrameProcessor):
    """Única responsabilidade: redimensionar a imagem para target_width/target_height."""

    name = "resize"

    def __init__(self, settings: WorkerSettings) -> None:
        self._target_width = settings.target_width
        self._target_height = settings.target_height

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.enable_resize

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        start = time.monotonic()
        resized = resize_frame(Frame(image=frame, metadata=metadata), self._target_width, self._target_height)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return resized.image, resized.metadata, context
