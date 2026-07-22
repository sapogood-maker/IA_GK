"""StatisticsProcessor: não transforma a imagem — só prova que um Processor
pode existir exclusivamente para medir, sem alterar nenhum pixel."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.metadata import FrameMetadata


class StatisticsProcessor(FrameProcessor):
    """Única responsabilidade: registrar que este frame foi processado - sem
    nenhuma detecção ou transformação de imagem."""

    name = "statistics"

    def __init__(self, settings: WorkerSettings) -> None:
        pass

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.enable_statistics_processor

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        start = time.monotonic()
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context
