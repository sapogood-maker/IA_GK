"""GoalkeeperPresenceAnalyzer: primeira implementação concreta da
Analyzer API (Sprint W13) - responde só perguntas factuais e
determinísticas sobre a presença do goleiro. Nenhuma heurística, nenhuma
regra de futebol, nenhuma avaliação, nenhum julgamento - totalmente
determinístico, sem nenhuma IA adicional."""
from __future__ import annotations

import time

from worker.analyzers.base import Analyzer
from worker.analyzers.results import AnalysisResult, AnalyzerMetadata, GoalkeeperPresenceResult
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld


class GoalkeeperPresenceAnalyzer(Analyzer):
    """Responde: existe um goleiro? quantos? qual track_id? está
    visível? há quantos frames existe? qual a posição/bbox atuais?

    Quando `FootballWorld.goalkeepers` tem mais de um candidato (o
    Football Domain Model, W12, nunca desambigua "qual É o goleiro de
    verdade"), esta implementação escolhe deterministicamente o PRIMEIRO
    da lista - uma regra de ordem, não uma heurística comportamental."""

    name = "goalkeeper_presence"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        """Não usa nenhum campo de `settings` hoje - mantém a assinatura
        uniforme já usada por toda implementação concreta desde a W4."""

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        goalkeepers = football_world.goalkeepers
        exists = len(goalkeepers) > 0
        selected = goalkeepers[0] if exists else None

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperPresenceResult(
            frame_index=football_world.frame_index,
            metadata=metadata,
            exists=exists,
            visible=selected.active if selected is not None else False,
            goalkeeper_count=len(goalkeepers),
            track_id=selected.track_id if selected is not None else None,
            age=selected.age if selected is not None else None,
            current_position=selected.position if selected is not None else None,
            current_bbox=selected.bbox if selected is not None else None,
        )
