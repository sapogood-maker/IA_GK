"""Interface única de todo SceneAnalyzer - SceneAnalyzer.

Contrato mínimo: `analyze(tracking_result) -> SceneAnalysisResult`. O
SceneAnalyzer nunca conhece ByteTrack/Ultralytics - só o contrato
`TrackingResult` (a saída de QUALQUER Tracker, Seção 6.1). Trocar o
analisador de cena por outro nunca exige alterar `SceneAnalysisProcessor`
nem qualquer outro Processor - só escrever uma nova classe que implemente
esta interface e registrá-la (`registry.py`).

Como `Tracker`, um `SceneAnalyzer` é inerentemente stateful (precisa
lembrar observações de trilhas entre chamadas sucessivas) - `reset()`
existe pelo mesmo motivo que `Tracker.reset()` (Seção 6.1, "Estado entre
Jobs")."""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.config.settings import WorkerSettings
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.trackers.types import TrackingResult


class SceneAnalyzer(ABC):
    """Uma única responsabilidade: interpretar um TrackingResult e
    produzir eventos de cena genéricos - nenhuma regra de negócio."""

    name: str
    version: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo SceneAnalyzer registrado é construído com `settings`
        (mesma convenção uniforme já usada por InferenceEngine/
        FrameProcessor/Detector/Tracker)."""

    @abstractmethod
    def analyze(self, tracking_result: TrackingResult) -> SceneAnalysisResult:
        """Interpreta o TrackingResult do frame atual, devolve um
        SceneAnalysisResult - nunca uma lista de dicionários solta."""
        ...

    def reset(self) -> None:
        """Limpa todo estado interno de observações. Chamado uma vez no
        início de cada Job/vídeo (via PipelineProcessor.reset(), Seção
        6.1) - sem isso, a mesma instância de SceneAnalyzer (reaproveitada
        por todo o ciclo de vida do processo do Worker) vazaria
        observações de um vídeo para o próximo. Default no-op."""
