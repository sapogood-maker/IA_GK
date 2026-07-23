"""Interface única de todo Analyzer - Analyzer (ABC).

Contrato mínimo: `analyze(football_world) -> AnalysisResult`. Um
Analyzer conhece APENAS `FootballWorld` (`worker.domain.football_world`)
- nunca `WorldState`, `SceneAnalysisResult`, `TrackingResult`,
`DetectionResult`, OpenCV, YOLO, ByteTrack, Redis, Backend ou R2. Trocar
ou adicionar um Analyzer nunca exige alterar `AnalyzerProcessor` nem
qualquer outro Analyzer - só escrever uma nova classe que implemente
esta interface e registrá-la (`registry.py`). É exatamente este contrato
que permite, ao final da W13, implementar `GoalkeeperPositionAnalyzer`/
`BallAnalyzer`/`ShotAnalyzer`/`SaveAnalyzer`/`DiveAnalyzer`/
`GoalAnalyzer` apenas criando um novo Analyzer e registrando-o."""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.analyzers.results import AnalysisResult
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld


class Analyzer(ABC):
    """Uma única responsabilidade: responder uma pergunta específica
    sobre um FootballWorld, devolvendo um AnalysisResult tipado."""

    name: str
    version: str

    def __init__(self, settings: WorkerSettings) -> None:
        """Todo Analyzer registrado é construído com `settings` (mesma
        convenção uniforme já usada por InferenceEngine/FrameProcessor/
        Detector/Tracker/SceneAnalyzer/WorldModel/FootballWorldBuilder)."""

    @abstractmethod
    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        """Analisa o FootballWorld do frame atual, devolve o
        AnalysisResult correspondente - nunca uma lista de dicionários
        solta, nunca conhece nada abaixo de FootballWorld."""
        ...

    def reset(self) -> None:
        """Limpa qualquer estado interno acumulado entre Jobs (mesma
        plumbing desde a W9, Seção 6.1, "Estado entre Jobs"). Default
        no-op - a maioria dos Analyzers é sem estado, já que cada
        FootballWorld já é uma fotografia completa do frame atual;
        sobrescrever apenas se um Analyzer futuro precisar lembrar de
        frames anteriores (ex.: um ShotAnalyzer que acumule velocidade da
        bola ao longo do tempo)."""
