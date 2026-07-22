"""SceneAnalysisProcessor: Processor que interpreta a cena a partir do
tracking - primeira implementação concreta a usar a API de Eventos de
Cena (Sprint W10).

Nenhuma regra de negócio aqui: só recebe o `TrackingResult` mais recente
do contexto (produzido por `TrackingProcessor` no MESMO frame, mais cedo
na mesma execução da pipeline), chama `SceneAnalyzer.analyze()` (resolvido
pela `factory` a partir de `WORKER_SCENE_ANALYZER`), acumula o
`SceneAnalysisResult` no contexto e continua a pipeline sem alterar a
imagem."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.events.factory import create_analyzer
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.metadata import FrameMetadata


class SceneAnalysisProcessor(FrameProcessor):
    """Única responsabilidade: interpretar o TrackingResult do frame
    atual e registrar os eventos de cena no contexto - nunca transforma a
    imagem, nunca detecta ou rastreia por conta própria."""

    name = "scene_analysis"

    def __init__(self, settings: WorkerSettings) -> None:
        self._analyzer = create_analyzer(settings.scene_analyzer, settings)

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.scene_analysis_enabled and bool(settings.scene_analyzer)

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        if not context.tracking_results:
            # Nenhum Processor de tracking rodou neste frame (ex.:
            # TrackingProcessor desabilitado) - nada para interpretar.
            return frame, metadata, context

        start = time.monotonic()
        latest_tracking_result = context.tracking_results[-1]
        result = self._analyzer.analyze(latest_tracking_result)
        context.add_scene_analysis_result(result)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context

    def reset(self) -> None:
        self._analyzer.reset()
