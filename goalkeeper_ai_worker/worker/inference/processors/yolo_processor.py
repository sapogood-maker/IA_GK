"""YOLOProcessor: Processor que detecta objetos no frame - primeira
implementação concreta a usar a API de Detecção (Sprint W8).

Nenhuma lógica de modelo aqui: só recebe o frame, chama `Detector.detect()`
(resolvido pela `factory` a partir de `WORKER_DETECTOR`), acumula o
`DetectionResult` no contexto e continua a pipeline sem alterar a
imagem. Nenhum código Ultralytics, nenhum peso, nenhum modelo é
conhecido por este Processor - só o contrato `Detector`."""
from __future__ import annotations

import time
from dataclasses import replace

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.detectors.factory import create_detector
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.metadata import FrameMetadata


class YOLOProcessor(FrameProcessor):
    """Única responsabilidade: detectar objetos no frame e registrar o
    resultado no contexto - nunca transforma a imagem em si."""

    name = "yolo"

    def __init__(self, settings: WorkerSettings) -> None:
        self._detector = create_detector(settings.detector, settings)

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return bool(settings.detector)

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        start = time.monotonic()
        result = self._detector.detect(frame)
        result = replace(result, frame_index=metadata.frame_index)
        context.add_detection_result(result)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context
