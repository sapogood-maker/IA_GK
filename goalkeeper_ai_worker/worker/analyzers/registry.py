"""Registry de Analyzers - guarda quais classes de Analyzer estão
disponíveis, por nome.

Especialização do Plugin Registry (AI_WORKER_CONSTITUTION.md, Seção 6)
para a família de Analyzers - paralela ao Registry de motores, de
Processors, de Detectors, de Trackers, de SceneAnalyzers e de
WorldModels, cada um independente. Diferente das famílias anteriores
(onde só UMA implementação fica ativa por vez, resolvida por
`WORKER_X`), vários Analyzers podem estar ativos SIMULTANEAMENTE
(`WORKER_ANALYZERS`, uma lista) - cada um responde uma pergunta
independente sobre o mesmo FootballWorld, não são substitutos uns dos
outros. Adicionar um Analyzer novo: escrever uma classe que implementa
`Analyzer` (base.py) e chamar `register_analyzer` com ela - nenhuma
mudança em `AnalyzerProcessor`, `factory.py` ou no restante do Worker."""
from __future__ import annotations

from worker.analyzers.ball_motion import BallMotionAnalyzer
from worker.analyzers.ball_position import BallPositionAnalyzer
from worker.analyzers.ball_trajectory import BallTrajectoryAnalyzer
from worker.analyzers.base import Analyzer
from worker.analyzers.goal_geometry import GoalGeometryAnalyzer
from worker.analyzers.goalkeeper_analysis_report import GoalkeeperAnalysisReportAnalyzer
from worker.analyzers.goalkeeper_ball_alignment import GoalkeeperBallAlignmentAnalyzer
from worker.analyzers.goalkeeper_coaching import GoalkeeperCoachingAnalyzer
from worker.analyzers.goalkeeper_decision import GoalkeeperDecisionAnalyzer
from worker.analyzers.goalkeeper_decision_evaluation import GoalkeeperDecisionEvaluationAnalyzer
from worker.analyzers.goalkeeper_position import GoalkeeperPositionAnalyzer
from worker.analyzers.goalkeeper_performance_evaluation import GoalkeeperPerformanceEvaluationAnalyzer
from worker.analyzers.goalkeeper_presence import GoalkeeperPresenceAnalyzer
from worker.analyzers.play_outcome import PlayOutcomeAnalyzer
from worker.analyzers.play_situation import PlaySituationAnalyzer
from worker.analyzers.shot import ShotAnalyzer

_ANALYZERS: dict[str, type[Analyzer]] = {}


def register_analyzer(name: str, analyzer_class: type[Analyzer]) -> None:
    """Registra uma classe de Analyzer sob um nome."""
    _ANALYZERS[name] = analyzer_class


def get_analyzer_class(name: str) -> type[Analyzer] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _ANALYZERS.get(name)


def available_analyzers() -> list[str]:
    """Nomes de todos os Analyzers registrados no momento."""
    return sorted(_ANALYZERS)


register_analyzer("goalkeeper_presence", GoalkeeperPresenceAnalyzer)
register_analyzer("goal_geometry", GoalGeometryAnalyzer)
register_analyzer("goalkeeper_position", GoalkeeperPositionAnalyzer)
register_analyzer("ball_position", BallPositionAnalyzer)
register_analyzer("goalkeeper_ball_alignment", GoalkeeperBallAlignmentAnalyzer)
register_analyzer("ball_motion", BallMotionAnalyzer)
register_analyzer("shot", ShotAnalyzer)
register_analyzer("ball_trajectory", BallTrajectoryAnalyzer)
register_analyzer("play_situation", PlaySituationAnalyzer)
register_analyzer("goalkeeper_decision", GoalkeeperDecisionAnalyzer)
register_analyzer("goalkeeper_decision_evaluation", GoalkeeperDecisionEvaluationAnalyzer)
register_analyzer("play_outcome", PlayOutcomeAnalyzer)
register_analyzer("goalkeeper_performance_evaluation", GoalkeeperPerformanceEvaluationAnalyzer)
register_analyzer("goalkeeper_coaching", GoalkeeperCoachingAnalyzer)
register_analyzer("goalkeeper_analysis_report", GoalkeeperAnalysisReportAnalyzer)
