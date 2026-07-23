"""GoalkeeperAnalysisReportAnalyzer: consolidação final do MVP
arquitetural do Worker (Sprint W27) - responde APENAS "qual é a análise
COMPLETA e consolidada desta jogada?" (`GoalkeeperAnalysisReport`).
NÃO produz nenhuma conclusão nova, NÃO recalcula nada, NÃO executa
nenhuma regra nova - apenas AGREGA os seis resultados já produzidos
pelos Analyzers cognitivos existentes.

Cadeia completa desta arquitetura, agora CONSOLIDADA numa única saída:
Situação (W21, `PlaySituationAnalyzer`) → Decisão (W22,
`GoalkeeperDecisionAnalyzer`) → Avaliação da Decisão (W23,
`GoalkeeperDecisionEvaluationAnalyzer`) → Resultado (W24,
`PlayOutcomeAnalyzer`) → Avaliação de Desempenho (W25,
`GoalkeeperPerformanceEvaluationAnalyzer`) → Coaching (W26,
`GoalkeeperCoachingAnalyzer`) → Relatório Consolidado (W27, esta
sprint). Cada um dos seis Analyzers compostos já encerra, por si só,
toda a cadeia de camadas anteriores (ex.: `GoalkeeperCoachingAnalyzer`
já compõe `GoalkeeperPerformanceEvaluationAnalyzer`, que já compõe
`GoalkeeperDecisionEvaluationAnalyzer`, etc.) - esta sprint não precisa
descobrir nenhuma dependência nova, só instanciar os seis e ecoar seus
resultados.

Segue o padrão de composição estabelecido nas W14-W26: instancia
`PlaySituationAnalyzer`/`GoalkeeperDecisionAnalyzer`/
`GoalkeeperDecisionEvaluationAnalyzer`/`PlayOutcomeAnalyzer`/
`GoalkeeperPerformanceEvaluationAnalyzer`/`GoalkeeperCoachingAnalyzer`
internamente e chama `.analyze(football_world)` como função pura em
cada um - nenhum canal de comunicação especial entre Analyzers, nenhuma
mudança em `AnalyzerProcessor`/`ProcessorContext`. Sem `AnalyzerContext`
próprio - quinto combinador puro (depois de `PlaySituationAnalyzer`/W21,
`GoalkeeperDecisionEvaluationAnalyzer`/W23,
`GoalkeeperPerformanceEvaluationAnalyzer`/W25 e
`GoalkeeperCoachingAnalyzer`/W26) - este Analyzer nunca precisa lembrar
nada entre frames, já que cada um dos seis compostos já mantém seu
próprio estado (ou não precisa de nenhum)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from worker import __version__ as WORKER_VERSION
from worker.analyzers.base import Analyzer
from worker.analyzers.goalkeeper_coaching import GoalkeeperCoachingAnalyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.results import (
    AnalysisResult,
    AnalyzerMetadata,
    GoalkeeperAnalysisReport,
    GoalkeeperCoachingResult,
    GoalkeeperDecisionEvaluationResult,
    GoalkeeperDecisionResult,
    GoalkeeperPerformanceEvaluationResult,
    PlayOutcomeResult,
    PlaySituationResult,
)
from worker.analyzers.types import AnalyzerName, AnalyzerVersion
from worker.config.settings import WorkerSettings
from worker.domain.football_world import FootballWorld

# Versao do ESQUEMA deste relatorio consolidado - distinta de
# WORKER_VERSION (versao do software), mesmo principio de
# WORKER_PROTOCOL_VERSION vs. worker.__version__ (Sprint W2). Muda só
# quando a FORMA do GoalkeeperAnalysisReport mudar, nao a cada release
# do Worker.
_REPORT_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class _ComposedResults:
    """Agrupamento PURO dos seis resultados já produzidos - nenhum
    campo aqui é recalculado, todos são ecoados diretamente dos
    Analyzers compostos."""

    play_situation: PlaySituationResult
    goalkeeper_decision: GoalkeeperDecisionResult
    decision_evaluation: GoalkeeperDecisionEvaluationResult
    play_outcome: PlayOutcomeResult
    performance_evaluation: GoalkeeperPerformanceEvaluationResult
    coaching: GoalkeeperCoachingResult


class GoalkeeperAnalysisReportAnalyzer(Analyzer):
    """Responde apenas: "qual é a análise completa e consolidada desta
    jogada?" - agregação pura dos seis resultados cognitivos já
    produzidos, nunca uma nova conclusão, nunca uma nova regra."""

    name = "goalkeeper_analysis_report"
    version = "1.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._play_situation_analyzer = PlaySituationAnalyzer(settings)
        self._goalkeeper_decision_analyzer = GoalkeeperDecisionAnalyzer(settings)
        self._goalkeeper_decision_evaluation_analyzer = GoalkeeperDecisionEvaluationAnalyzer(settings)
        self._play_outcome_analyzer = PlayOutcomeAnalyzer(settings)
        self._goalkeeper_performance_evaluation_analyzer = GoalkeeperPerformanceEvaluationAnalyzer(settings)
        self._goalkeeper_coaching_analyzer = GoalkeeperCoachingAnalyzer(settings)

    def analyze(self, football_world: FootballWorld) -> AnalysisResult:
        start = time.monotonic()

        results = self._compose(football_world)

        confidence_summary = self._build_confidence_summary(results)
        artifacts = self._build_artifacts(results)

        metadata = AnalyzerMetadata(
            analyzer_name=AnalyzerName(self.name),
            analyzer_version=AnalyzerVersion(self.version),
            processing_time_ms=(time.monotonic() - start) * 1000,
        )
        return GoalkeeperAnalysisReport(
            frame_index=football_world.frame_index,
            metadata=metadata,
            play_situation=results.play_situation,
            goalkeeper_decision=results.goalkeeper_decision,
            decision_evaluation=results.decision_evaluation,
            play_outcome=results.play_outcome,
            performance_evaluation=results.performance_evaluation,
            coaching=results.coaching,
            confidence_summary=confidence_summary,
            artifacts=artifacts,
            analysis_version=_REPORT_SCHEMA_VERSION,
            worker_version=WORKER_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compose(self, football_world: FootballWorld) -> _ComposedResults:
        """Chama cada um dos seis Analyzers como função pura sobre o
        MESMO `football_world` - nenhum recalcula nada que outro já
        tenha produzido; cada um internamente já compõe (ou não precisa
        de) todas as camadas anteriores por conta própria."""
        return _ComposedResults(
            play_situation=self._play_situation_analyzer.analyze(football_world),
            goalkeeper_decision=self._goalkeeper_decision_analyzer.analyze(football_world),
            decision_evaluation=self._goalkeeper_decision_evaluation_analyzer.analyze(football_world),
            play_outcome=self._play_outcome_analyzer.analyze(football_world),
            performance_evaluation=self._goalkeeper_performance_evaluation_analyzer.analyze(football_world),
            coaching=self._goalkeeper_coaching_analyzer.analyze(football_world),
        )

    @staticmethod
    def _build_confidence_summary(results: _ComposedResults) -> dict:
        """CONSOLIDA (nunca recalcula) as seis `confidence`s já
        produzidas. `overall` é o `min()` das seis, só quando TODAS
        estão disponíveis - mesmo princípio de "nunca fabricar uma
        confidence" já aplicado por todo Analyzer composto desde a
        W17."""
        per_analyzer = {
            "play_situation": results.play_situation.confidence,
            "goalkeeper_decision": results.goalkeeper_decision.confidence,
            "goalkeeper_decision_evaluation": results.decision_evaluation.confidence,
            "play_outcome": results.play_outcome.confidence,
            "goalkeeper_performance_evaluation": results.performance_evaluation.confidence,
            "goalkeeper_coaching": results.coaching.confidence,
        }
        overall = None
        if all(value is not None for value in per_analyzer.values()):
            overall = min(per_analyzer.values())
        return {**per_analyzer, "overall": overall}

    @staticmethod
    def _build_artifacts(results: _ComposedResults) -> dict:
        """Espelho de conveniência dos mesmos seis sub-resultados,
        indexado por nome de Analyzer (mesma convenção de
        `analysis_results` desde a W13) - permite a um consumidor
        genérico iterar por nome sem precisar conhecer os seis campos
        tipados de antemão. Preserva INTEGRALMENTE cada payload (via
        `to_dict()` de cada um) - nunca remove `rules_evaluated`/
        `rules_passed`/`rules_failed`/`explanations`/`summary`/
        `supporting_evidence`."""
        return {
            "play_situation": results.play_situation.to_dict(),
            "goalkeeper_decision": results.goalkeeper_decision.to_dict(),
            "goalkeeper_decision_evaluation": results.decision_evaluation.to_dict(),
            "play_outcome": results.play_outcome.to_dict(),
            "goalkeeper_performance_evaluation": results.performance_evaluation.to_dict(),
            "goalkeeper_coaching": results.coaching.to_dict(),
        }

    def reset(self) -> None:
        """Delega `reset()` aos seis Analyzers compostos - alguns deles
        (transitivamente) são genuinamente STATEFUL; este Analyzer não
        tem `AnalyzerContext` próprio - combinador puro, mesmo padrão de
        `PlaySituationAnalyzer` (W21), `GoalkeeperDecisionEvaluationAnalyzer`
        (W23), `GoalkeeperPerformanceEvaluationAnalyzer` (W25) e
        `GoalkeeperCoachingAnalyzer` (W26)."""
        self._play_situation_analyzer.reset()
        self._goalkeeper_decision_analyzer.reset()
        self._goalkeeper_decision_evaluation_analyzer.reset()
        self._play_outcome_analyzer.reset()
        self._goalkeeper_performance_evaluation_analyzer.reset()
        self._goalkeeper_coaching_analyzer.reset()
