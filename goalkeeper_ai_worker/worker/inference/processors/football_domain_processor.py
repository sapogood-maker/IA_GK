"""FootballDomainProcessor: Processor que transforma o estado do mundo em
domínio de futebol - primeira implementação concreta a usar o Football
Domain Model (Sprint W12).

Nenhuma regra de negócio aqui: só recebe o `WorldState` mais recente do
contexto (produzido por `WorldModelProcessor` no MESMO frame, mais cedo
na mesma execução da pipeline), chama `FootballWorldBuilder.build()`,
acumula o `FootballWorld` no contexto e continua a pipeline sem alterar
a imagem.

Diferente de `YOLOProcessor`/`TrackingProcessor`/`SceneAnalysisProcessor`/
`WorldModelProcessor`, não há `factory.py`/`registry.py` para esta
camada - `FootballWorldBuilder` é a única implementação do domínio, não
uma família de Plugin substituível (Seção 6, AI_WORKER_CONSTITUTION.md)."""
from __future__ import annotations

import time

import numpy as np

from worker.config.settings import WorkerSettings
from worker.domain.world_builder import FootballWorldBuilder
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.metadata import FrameMetadata


class FootballDomainProcessor(FrameProcessor):
    """Única responsabilidade: transformar o WorldState do frame atual em
    FootballWorld e registrar o resultado no contexto - nunca transforma
    a imagem, nunca detecta, rastreia, interpreta cena ou mantém estado
    genérico por conta própria."""

    name = "football_domain"

    def __init__(self, settings: WorkerSettings) -> None:
        self._builder = FootballWorldBuilder(settings)

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return settings.football_domain_enabled

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        if not context.world_states:
            # Nenhum Processor de World Model rodou neste frame (ex.:
            # WorldModelProcessor desabilitado) - nada para transformar.
            return frame, metadata, context

        start = time.monotonic()
        latest_world_state = context.world_states[-1]
        football_world = self._builder.build(latest_world_state)
        context.add_football_world(football_world)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context

    def reset(self) -> None:
        self._builder.reset()
