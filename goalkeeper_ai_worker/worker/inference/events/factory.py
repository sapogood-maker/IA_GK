"""Ponto único de resolução do SceneAnalyzer ativo, a partir de
configuração (WORKER_SCENE_ANALYZER) - nunca hardcoded em nenhum
Processor.

Espelha `inference/trackers/factory.py` (create_tracker) para a família
de Eventos de Cena."""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.exceptions import SceneAnalysisInitializationError
from worker.inference.events.registry import available_analyzers, get_analyzer_class


def create_analyzer(analyzer_name: str, settings: WorkerSettings) -> SceneAnalyzer:
    """Instancia o SceneAnalyzer correspondente a `analyzer_name`.

    Levanta SceneAnalysisInitializationError se `analyzer_name` não
    estiver registrado, ou se a própria inicialização falhar - nunca faz
    fallback silencioso para outro SceneAnalyzer."""
    analyzer_class = get_analyzer_class(analyzer_name)
    if analyzer_class is None:
        raise SceneAnalysisInitializationError(
            f"SceneAnalyzer desconhecido: '{analyzer_name}'. "
            f"Disponiveis: {', '.join(available_analyzers())}"
        )
    try:
        return analyzer_class(settings)
    except SceneAnalysisInitializationError:
        raise
    except Exception as exc:
        raise SceneAnalysisInitializationError(
            f"Falha ao inicializar o SceneAnalyzer '{analyzer_name}': {exc}"
        ) from exc
