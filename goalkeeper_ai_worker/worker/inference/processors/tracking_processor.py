"""TrackingProcessor: Processor que associa detecções entre frames -
primeira implementação concreta a usar a API de Tracking (Sprint W9).

Nenhuma lógica de ByteTrack (ou de qualquer outro algoritmo de tracking)
aqui: só recebe o `DetectionResult` mais recente do contexto (produzido
por `YOLOProcessor` no MESMO frame, mais cedo na mesma execução da
pipeline), chama `Tracker.track()` (resolvido pela `factory` a partir de
`WORKER_TRACKER`), acumula o `TrackingResult` no contexto e continua a
pipeline sem alterar a imagem."""
from __future__ import annotations

import time
from dataclasses import replace

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.inference.trackers.factory import create_tracker
from worker.video.metadata import FrameMetadata


class TrackingProcessor(FrameProcessor):
    """Única responsabilidade: associar as detecções do frame atual às
    trilhas existentes e registrar o resultado no contexto - nunca
    transforma a imagem em si, nunca detecta por conta própria."""

    name = "tracking"

    def __init__(self, settings: WorkerSettings) -> None:
        self._tracker = create_tracker(settings.tracker, settings)

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.tracking_enabled and bool(settings.tracker)

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        if not context.detections:
            # Nenhum Processor de deteccao rodou neste frame (ex.: YOLOProcessor
            # desabilitado) - nada para associar a trilhas.
            return frame, metadata, context

        start = time.monotonic()
        latest_detections = context.detections[-1]
        result = self._tracker.track(latest_detections)
        result = replace(
            result,
            frame_index=metadata.frame_index,
            tracked_objects=[
                replace(obj, frame_index=metadata.frame_index) for obj in result.tracked_objects
            ],
        )
        context.add_tracking_result(result)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context

    def reset(self) -> None:
        self._tracker.reset()
