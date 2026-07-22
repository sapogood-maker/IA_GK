"""SceneAnalysisContext: memória interna de um SceneAnalyzer entre
chamadas sucessivas a `analyze()` - NÃO é o `ProcessorContext` do pipeline
(este último acumula resultados de TODOS os Processors ao longo de um
Job; este aqui é privado de uma única instância de SceneAnalyzer, do
mesmo jeito que `ByteTrackTracker` mantém sua própria lista de trilhas
internamente).

Um `SceneAnalyzer` é inerentemente stateful (precisa lembrar a última
posição/estado de cada trilha para detectar transições) - por isso
`reset()`, chamado no início de cada Job (via `FrameProcessor.reset()` /
`PipelineProcessor.reset()`, Sprint W9) para não vazar observações de um
vídeo para o próximo."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.inference.events.types import MotionState, TrackLifecycle
from worker.inference.trackers.types import BoundingBox


@dataclass
class TrackObservation:
    """Última observação conhecida de uma trilha específica."""

    track_id: int
    label: str
    bbox: BoundingBox
    last_seen_frame: int
    lifecycle: TrackLifecycle
    motion_state: MotionState = MotionState.UNKNOWN


@dataclass
class SceneAnalysisContext:
    """Observações por `track_id`, mantidas entre chamadas a `analyze()`."""

    observations: dict[int, TrackObservation] = field(default_factory=dict)

    def reset(self) -> None:
        """Limpa toda observação - chamado no início de cada Job."""
        self.observations.clear()
