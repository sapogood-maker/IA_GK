"""Interface única de todo Processor de frame — FrameProcessor.

Nenhum Processor conhece outro Processor: recebe `frame`/`metadata`/
`context` e devolve os três atualizados. Adicionar um Processor novo
(ex.: `YOLOProcessor` na W8) nunca exige alterar `PipelineProcessor` nem
qualquer Processor existente — só implementar esta interface, registrá-lo
e declarar seu próprio `is_enabled()`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from worker.analyzers.results import AnalysisResult
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld
from worker.inference.detectors.types import DetectionResult
from worker.inference.events.types import SceneAnalysisResult
from worker.inference.trackers.types import TrackingResult
from worker.inference.world.world_state import WorldState
from worker.video.metadata import FrameMetadata


@dataclass
class ProcessorStats:
    """Estatísticas acumuladas por um único Processor ao longo da pipeline."""

    processor_name: str
    frames_processed: int = 0
    total_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "frames_processed": self.frames_processed,
            "total_time_ms": self.total_time_ms,
        }


@dataclass
class ProcessorContext:
    """Estado compartilhado entre Processors ao longo de uma execução da
    pipeline — acumula estatísticas por Processor (tempo de execução,
    frames processados), resultados de detecção (Sprint W8), resultados
    de tracking (Sprint W9), resultados de análise de cena (Sprint W10),
    estados do mundo (Sprint W11), estados de domínio de futebol
    (Sprint W12) e resultados de análise (Sprint W13), que entram no
    artefato JSON final."""

    stats: dict[str, ProcessorStats] = field(default_factory=dict)
    detections: list[DetectionResult] = field(default_factory=list)
    tracking_results: list[TrackingResult] = field(default_factory=list)
    scene_analysis_results: list[SceneAnalysisResult] = field(default_factory=list)
    world_states: list[WorldState] = field(default_factory=list)
    football_worlds: list[FootballWorld] = field(default_factory=list)
    analysis_results: list[AnalysisResult] = field(default_factory=list)

    def record(self, processor_name: str, duration_ms: float) -> None:
        """Registra que `processor_name` processou mais um frame, levando `duration_ms`."""
        stat = self.stats.setdefault(processor_name, ProcessorStats(processor_name=processor_name))
        stat.frames_processed += 1
        stat.total_time_ms += duration_ms

    def add_detection_result(self, result: DetectionResult) -> None:
        """Acumula o `DetectionResult` de um frame - usado por qualquer
        Processor de detecção (hoje só `YOLOProcessor`), nunca lido por
        outro Processor - só pelo motor, após a pipeline terminar (ou por
        `TrackingProcessor`, que lê a última entrada do MESMO frame)."""
        self.detections.append(result)

    def add_tracking_result(self, result: TrackingResult) -> None:
        """Acumula o `TrackingResult` de um frame - usado por qualquer
        Processor de tracking (hoje só `TrackingProcessor`), lido só pelo
        motor, após a pipeline terminar (ou por `SceneAnalysisProcessor`,
        que lê a última entrada do MESMO frame)."""
        self.tracking_results.append(result)

    def add_scene_analysis_result(self, result: SceneAnalysisResult) -> None:
        """Acumula o `SceneAnalysisResult` de um frame - usado por
        qualquer Processor de análise de cena (hoje só
        `SceneAnalysisProcessor`), lido só pelo motor, após a pipeline
        terminar (ou por `WorldModelProcessor`, que lê a última entrada
        do MESMO frame)."""
        self.scene_analysis_results.append(result)

    def add_world_state(self, state: WorldState) -> None:
        """Acumula o `WorldState` de um frame - usado por qualquer
        Processor de World Model (hoje só `WorldModelProcessor`), lido só
        pelo motor, após a pipeline terminar (ou por
        `FootballDomainProcessor`, que lê a última entrada do MESMO frame)."""
        self.world_states.append(state)

    def add_football_world(self, football_world: FootballWorld) -> None:
        """Acumula o `FootballWorld` de um frame - usado por qualquer
        Processor de domínio de futebol (hoje só
        `FootballDomainProcessor`), lido só pelo motor, após a pipeline
        terminar."""
        self.football_worlds.append(football_world)

    def add_analysis_result(self, result: AnalysisResult) -> None:
        """Acumula um `AnalysisResult` (de um Analyzer, para um frame) -
        usado por `AnalyzerProcessor` (Sprint W13, `worker.analyzers.
        processor`), lido só pelo motor, após a pipeline terminar. Vários
        Analyzers ativos produzem várias entradas para o MESMO frame -
        diferente de `add_world_state`/`add_football_world` (uma única
        implementação ativa por vez)."""
        self.analysis_results.append(result)

    def to_dict(self) -> dict:
        return {name: stat.to_dict() for name, stat in self.stats.items()}

    def detections_to_dict(self) -> list[dict]:
        return [result.to_dict() for result in self.detections]

    def tracking_results_to_dict(self) -> list[dict]:
        return [result.to_dict() for result in self.tracking_results]

    def scene_events_to_dict(self) -> list[dict]:
        """Achata os eventos de TODOS os SceneAnalysisResults acumulados
        numa única lista cronológica - o que entra no artefato como
        `"scene_events"` (Sprint W10)."""
        return [
            event.to_dict()
            for result in self.scene_analysis_results
            for event in result.events
        ]


class FrameProcessor(ABC):
    """Uma única etapa de transformação/medição de frame."""

    name: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo Processor registrado é construído com `settings` (mesma
        convenção uniforme já usada por `InferenceEngine`, Sprint W6) — cada
        Processor lê só o que precisa, ignora o resto."""

    @classmethod
    @abstractmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        """Decide, a partir da configuração, se este Processor entra na
        pipeline — sem exigir nenhuma mudança em `pipeline.py`/`registry.py`
        para habilitar/desabilitar um Processor novo."""
        ...

    @abstractmethod
    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        """Transforma (ou só mede) o frame, devolvendo frame/metadata/context atualizados."""
        ...

    def reset(self) -> None:
        """Limpa qualquer estado interno acumulado entre Jobs (Sprint W9).

        A mesma instância de Processor é reaproveitada por todo o ciclo
        de vida do processo do Worker (construída uma vez em
        `WorkerOrchestrator.__init__`, nunca por Job) - Processors sem
        estado (Color/Resize/ROI/Statistics/YOLO) não precisam sobrescrever
        isto. `TrackingProcessor` sobrescreve para evitar vazar TrackIds de
        um vídeo para o próximo."""
