"""Ponto único de resolução de um Analyzer ativo, a partir de
configuração (WORKER_ANALYZERS) - nunca hardcoded em nenhum Processor.

Espelha `inference/world/factory.py` (create_world_model) para a família
de Analyzers - diferença: `AnalyzerProcessor` chama `create_analyzer` uma
vez POR NOME na lista de `WORKER_ANALYZERS`, não uma única vez para "o"
Analyzer ativo (várias implementações coexistem, ver `registry.py`)."""
from __future__ import annotations

from worker.analyzers.base import Analyzer
from worker.analyzers.exceptions import AnalyzerInitializationError
from worker.analyzers.registry import available_analyzers, get_analyzer_class
from worker.config.settings import WorkerSettings


def create_analyzer(analyzer_name: str, settings: WorkerSettings) -> Analyzer:
    """Instancia o Analyzer correspondente a `analyzer_name`.

    Levanta AnalyzerInitializationError se `analyzer_name` não estiver
    registrado, ou se a própria inicialização falhar - nunca faz fallback
    silencioso para outro Analyzer."""
    analyzer_class = get_analyzer_class(analyzer_name)
    if analyzer_class is None:
        raise AnalyzerInitializationError(
            f"Analyzer desconhecido: '{analyzer_name}'. "
            f"Disponiveis: {', '.join(available_analyzers())}"
        )
    try:
        return analyzer_class(settings)
    except AnalyzerInitializationError:
        raise
    except Exception as exc:
        raise AnalyzerInitializationError(
            f"Falha ao inicializar o Analyzer '{analyzer_name}': {exc}"
        ) from exc
