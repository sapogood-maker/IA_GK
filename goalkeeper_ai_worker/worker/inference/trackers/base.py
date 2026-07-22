"""Interface única de todo Tracker - Tracker.

Contrato mínimo: `track(detections) -> TrackingResult`. O Tracker nunca
conhece YOLO/Ultralytics - só o contrato `DetectionResult` (a saída de
QUALQUER Detector, Seção 6.1). Trocar ByteTrack por BoT-SORT/DeepSORT/
StrongSORT/OC-SORT nunca exige alterar `TrackingProcessor` nem qualquer
outro Processor - só escrever uma nova classe que implemente esta
interface e registrá-la (`registry.py`).

Diferente de `Detector` (stateless - cada `detect(frame)` é independente),
um Tracker é inerentemente stateful: precisa lembrar trilhas entre
chamadas sucessivas. `reset()` existe para permitir que a MESMA instância
de Tracker (carregada uma vez por processo do Worker) seja reaproveitada
entre Jobs sem vazar identidade de trilhas de um vídeo para o próximo -
ver AI_WORKER_CONSTITUTION.md, Seção 6.1 (Risco de estado entre Jobs)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.config.settings import WorkerSettings
from worker.inference.detectors.types import DetectionResult
from worker.inference.trackers.types import TrackingResult


class Tracker(ABC):
    """Uma única responsabilidade: associar detecções entre frames,
    produzindo objetos com identidade persistente (`TrackId`)."""

    name: str
    version: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo Tracker registrado é construído com `settings` (mesma
        convenção uniforme já usada por InferenceEngine/FrameProcessor/
        Detector)."""

    @abstractmethod
    def track(self, detections: DetectionResult) -> TrackingResult:
        """Recebe as detecções do frame atual, devolve um TrackingResult -
        nunca uma lista de dicionários solta."""
        ...

    def reset(self) -> None:
        """Limpa todo estado interno de trilhas. Chamado uma vez no início
        de cada Job/vídeo (via PipelineProcessor.reset(), Seção 6.1) - sem
        isso, a mesma instância de Tracker (reaproveitada por todo o
        ciclo de vida do processo do Worker) vazaria TrackIds de um vídeo
        para o próximo. Default no-op - Trackers sem estado podem ignorar."""
