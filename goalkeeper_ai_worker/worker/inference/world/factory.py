"""Ponto único de resolução do WorldModel ativo, a partir de
configuração (WORKER_WORLD_MODEL) - nunca hardcoded em nenhum Processor.

Espelha `inference/events/factory.py` (create_analyzer) para a família
de World Models."""
from __future__ import annotations

from worker.config.settings import WorkerSettings
from worker.inference.world.base import WorldModel
from worker.inference.world.exceptions import WorldModelInitializationError
from worker.inference.world.registry import available_world_models, get_world_model_class


def create_world_model(world_model_name: str, settings: WorkerSettings) -> WorldModel:
    """Instancia o WorldModel correspondente a `world_model_name`.

    Levanta WorldModelInitializationError se `world_model_name` não
    estiver registrado, ou se a própria inicialização falhar - nunca faz
    fallback silencioso para outro WorldModel."""
    world_model_class = get_world_model_class(world_model_name)
    if world_model_class is None:
        raise WorldModelInitializationError(
            f"WorldModel desconhecido: '{world_model_name}'. "
            f"Disponiveis: {', '.join(available_world_models())}"
        )
    try:
        return world_model_class(settings)
    except WorldModelInitializationError:
        raise
    except Exception as exc:
        raise WorldModelInitializationError(
            f"Falha ao inicializar o WorldModel '{world_model_name}': {exc}"
        ) from exc
