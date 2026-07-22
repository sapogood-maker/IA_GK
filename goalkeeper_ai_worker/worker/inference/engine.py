"""Ponto unico de resolucao do motor de inferencia ativo, a partir de
configuracao (WORKER_INFERENCE_ENGINE) - nunca hardcoded no Pipeline ou no
Orchestrator.

Sprint W6: todo motor registrado passa a ser construido com `settings`
(convencao uniforme de construtor do Registry) - `BasicVisionEngine`
precisa dela para resolver frame_skip/resize/ROI; `FakeInferenceEngine`
a recebe mas ignora.
"""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.inference.base import InferenceEngine
from worker.inference.exceptions import EngineInitializationError
from worker.inference.registry import available_engines, get_engine_class


def create_engine(engine_name: str, settings: WorkerSettings) -> InferenceEngine:
    """Instancia o InferenceEngine correspondente a `engine_name`.

    Levanta EngineInitializationError se `engine_name` nao estiver
    registrado - nunca faz fallback silencioso para outro motor."""
    engine_class = get_engine_class(engine_name)
    if engine_class is None:
        raise EngineInitializationError(
            f"Motor de inferencia desconhecido: '{engine_name}'. "
            f"Disponiveis: {', '.join(available_engines())}"
        )
    return engine_class(settings)
