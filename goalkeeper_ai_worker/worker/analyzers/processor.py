"""AnalyzerProcessor: Processor que faz a ponte entre a Analyzer API
(`worker/analyzers/`) e a pipeline de frames (`worker/inference/
processors/`) - primeira implementação concreta a rodar Analyzers reais
(Sprint W13).

Nenhuma regra de negócio aqui: só recebe o `FootballWorld` mais recente
do contexto (produzido por `FootballDomainProcessor` no MESMO frame, mais
cedo na mesma execução da pipeline), chama `Analyzer.analyze()` para cada
Analyzer ativo (resolvidos pela `factory` a partir de
`WORKER_ANALYZERS`), acumula cada `AnalysisResult` no contexto e continua
a pipeline sem alterar a imagem.

Diferente de `WorldModelProcessor`/`FootballDomainProcessor` (que
delegam a UMA única implementação ativa), este Processor mantém uma
LISTA de Analyzers - vários podem rodar simultaneamente sobre o mesmo
FootballWorld, cada um respondendo uma pergunta independente.

Sprint W14 (`GoalGeometryAnalyzer`, primeiro Analyzer puramente
geométrico) confirmou na prática que esta classe não precisa de NENHUMA
mudança para ganhar um segundo Analyzer ativo simultâneo - só registrar
a nova classe em `registry.py` e incluir seu nome em `WORKER_ANALYZERS`.
Um Analyzer futuro que precise compor o resultado de outro (ex.: um
`GoalkeeperPositionAnalyzer` que precise de `GoalGeometryResult`) NÃO
exige mudança aqui nem no contrato `Analyzer.analyze(football_world)` -
ele apenas instancia o Analyzer geométrico internamente e chama
`.analyze(football_world)` como uma função pura reutilizável (mesmo
`FootballWorld` que ele próprio já recebe), sem nenhum canal de
comunicação entre Analyzers precisar existir neste Processor."""
from __future__ import annotations

import time

import numpy as np

from worker.analyzers.factory import create_analyzer
from worker.config.settings import WorkerSettings
from worker.inference.processors.base import FrameProcessor, ProcessorContext
from worker.video.metadata import FrameMetadata


class AnalyzerProcessor(FrameProcessor):
    """Única responsabilidade: rodar cada Analyzer ativo contra o
    FootballWorld do frame atual e registrar os AnalysisResults
    resultantes no contexto - nunca transforma a imagem, nunca detecta,
    rastreia, interpreta cena, mantém estado genérico ou modela domínio
    por conta própria."""

    name = "analyzer"

    def __init__(self, settings: WorkerSettings) -> None:
        self._analyzers = [
            create_analyzer(analyzer_name, settings) for analyzer_name in settings.analyzer_names
        ]

    @classmethod
    def is_enabled(cls, settings: WorkerSettings) -> bool:
        return bool(settings.analyzer_names)

    def process(
        self, frame: np.ndarray, metadata: FrameMetadata, context: ProcessorContext
    ) -> tuple[np.ndarray, FrameMetadata, ProcessorContext]:
        if not context.football_worlds:
            # Nenhum FootballDomainProcessor rodou neste frame (ex.:
            # WORKER_FOOTBALL_DOMAIN_ENABLED=false) - nada para analisar.
            return frame, metadata, context

        start = time.monotonic()
        latest_football_world = context.football_worlds[-1]
        for analyzer in self._analyzers:
            result = analyzer.analyze(latest_football_world)
            context.add_analysis_result(result)
        context.record(self.name, (time.monotonic() - start) * 1000)
        return frame, metadata, context

    def reset(self) -> None:
        for analyzer in self._analyzers:
            analyzer.reset()
