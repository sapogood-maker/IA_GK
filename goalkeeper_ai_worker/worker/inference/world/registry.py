"""Registry de WorldModels - guarda quais classes de WorldModel estão
disponíveis, por nome.

Especialização do Plugin Registry (AI_WORKER_CONSTITUTION.md, Seção 6)
para a família de World Models - paralela ao Registry de motores, de
Processors, de Detectors, de Trackers e de SceneAnalyzers, cada um
independente. Adicionar um WorldModel novo: escrever uma classe que
implementa `WorldModel` (base.py) e chamar `register_world_model` com
ela - nenhuma mudança em `WorldModelProcessor`, `factory.py` ou no
restante do Worker."""
from __future__ import annotations

from worker.inference.world.base import WorldModel
from worker.inference.world.world_model import BasicWorldModel

_WORLD_MODELS: dict[str, type[WorldModel]] = {}


def register_world_model(name: str, world_model_class: type[WorldModel]) -> None:
    """Registra uma classe de WorldModel sob um nome."""
    _WORLD_MODELS[name] = world_model_class


def get_world_model_class(name: str) -> type[WorldModel] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _WORLD_MODELS.get(name)


def available_world_models() -> list[str]:
    """Nomes de todos os WorldModels registrados no momento."""
    return sorted(_WORLD_MODELS)


register_world_model("basic", BasicWorldModel)
