"""WorldModelProcessor: Processor que mantém o estado do mundo - primeira
implementação concreta a usar o World Model (Sprint W11).

Nenhuma regra de negócio aqui: só recebe o `SceneAnalysisResult` mais
recente do contexto (produzido por `SceneAnalysisProcessor` no MESMO
frame, mais cedo na mesma execução da pipeline), chama
`WorldModel.update()` (resolvido pela `factory` a partir de
`WORKER_WORLD_MODEL`), acumula o `WorldState` no contexto e continua a
pipeline sem alterar a imagem."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.inference.world.factory import create_world_model
from worker.video.metadata import FrameMetadata


class WorldModelProcessor(FrameProcessor):
    """Única responsabilidade: atualizar o World Model com o
    SceneAnalysisResult do frame atual e registrar o WorldState resultante
    no contexto - nunca transforma a imagem, nunca detecta, rastreia ou
    interpreta a cena por conta própria."""

    name = "world_model"

    def __init__(self, settings: WorkerSettings) -> None:
        self._world_model = create_world_model(settings.world_model, settings)

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.world_model_enabled and bool(settings.world_model)

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        if not context.scene_analysis_results:
            # Nenhum Processor de analise de cena rodou neste frame (ex.:
            # SceneAnalysisProcessor desabilitado) - nada para incorporar.
            return frame, metadata, context

        start = time.monotonic()
        latest_scene_result = context.scene_analysis_results[-1]
        world_state = self._world_model.update(latest_scene_result)
        context.add_world_state(world_state)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context

    def reset(self) -> None:
        self._world_model.reset()
