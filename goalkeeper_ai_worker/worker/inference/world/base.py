"""Interface única do World Model - WorldModel.

Contrato mínimo: `update(scene_result) -> WorldState`. O WorldModel
conhece apenas `SceneAnalysisResult` (`worker.inference.events.types`) -
nunca `Detector`, `Tracker`, OpenCV, YOLO, ByteTrack, Redis, Backend ou
R2. Trocar a implementação do World Model nunca exige alterar
`WorldModelProcessor` nem qualquer outro Processor - só escrever uma
nova classe que implemente esta interface e registrá-la (`registry.py`).

Como `Tracker`/`SceneAnalyzer`, um `WorldModel` é inerentemente stateful
(precisa lembrar objetos entre chamadas sucessivas) - `reset()` existe
pelo mesmo motivo: o estado pertence ao Job, nunca pode sobreviver entre
Jobs (Seção 6.1, "Estado entre Jobs")."""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.config.settings import WorkerSettings
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.world.world_state import WorldState


class WorldModel(ABC):
    """Uma única responsabilidade: manter um estado consistente do mundo
    observado, construído a partir de SceneAnalysisResults sucessivos."""

    name: str
    version: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo WorldModel registrado é construído com `settings` (mesma
        convenção uniforme já usada por InferenceEngine/FrameProcessor/
        Detector/Tracker/SceneAnalyzer)."""

    @abstractmethod
    def update(self, scene_result: SceneAnalysisResult) -> WorldState:
        """Incorpora o SceneAnalysisResult do frame atual, devolve o
        WorldState resultante - nunca uma lista de dicionários solta."""
        ...

    def reset(self) -> None:
        """Limpa todo estado interno de objetos. Chamado uma vez no
        início de cada Job/vídeo (via PipelineProcessor.reset(), Seção
        6.1) - sem isso, a mesma instância de WorldModel (reaproveitada
        por todo o ciclo de vida do processo do Worker) vazaria objetos
        de um vídeo para o próximo. Default no-op."""
