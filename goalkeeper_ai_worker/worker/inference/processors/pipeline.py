"""PipelineProcessor: executa a sequência de Processors registrados e
habilitados — responsável APENAS por orquestrar a execução. Nenhuma lógica
de transformação própria (isso vive em cada Processor).
"""
from __future__ import annotations

import numpy as np

from worker.config.settings import WorkerSettings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.inference.processors.registry import available_processors, get_processor_class
from worker.video.metadata import FrameMetadata


class PipelineProcessor:
    """Executa uma sequência ordenada de FrameProcessor sobre um frame."""

    def __init__(self, processors: list[FrameProcessor]) -> None:
        self._processors = processors

    @property
    def processor_names(self) -> list[str]:
        """Nomes dos Processors ativos nesta pipeline, na ordem de execução."""
        return [processor.name for processor in self._processors]

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        """Executa cada Processor em sequência - a saída de um é a entrada do próximo."""
        for processor in self._processors:
            frame, metadata, context = processor.process(frame, metadata, context)
        return frame, metadata, context

    def reset(self) -> None:
        """Chama `reset()` de cada Processor - usado por `BasicVisionEngine`
        no início de cada Job/vídeo (Sprint W9), já que a mesma
        `PipelineProcessor` é reaproveitada por todo o ciclo de vida do
        processo do Worker. `PipelineProcessor` não sabe QUAL Processor
        tem estado (ex.: `TrackingProcessor`) - só repassa o chamado."""
        for processor in self._processors:
            processor.reset()

    @classmethod
    def from_settings(cls, settings: WorkerSettings) -> PipelineProcessor:
        """Monta a pipeline com todos os Processors registrados que estão
        habilitados (`is_enabled(settings)`), na ordem em que foram
        registrados. Adicionar um Processor novo nunca exige alterar este
        método."""
        processors: list[FrameProcessor] = []
        for name in available_processors():
            processor_class = get_processor_class(name)
            if processor_class is not None and processor_class.is_enabled(settings):
                processors.append(processor_class(settings))
        return cls(processors)
