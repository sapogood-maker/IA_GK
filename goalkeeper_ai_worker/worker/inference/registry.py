"""Registry de motores de inferencia - guarda quais classes de
InferenceEngine estao disponiveis, por nome.

Especializacao do Plugin Registry (AI_WORKER_CONSTITUTION.md, Secao 6)
para a familia de motores de inferencia. Adicionar um motor novo (OpenCV,
YOLO, Pose, MultiModel): escrever uma classe que implementa
InferenceEngine (base.py) e chamar `register_engine` com ela - o Pipeline
nao muda.
"""
from __future__ import annotations

from worker.inference.base import InferenceEngine
from worker.inference.basic_vision_engine import BasicVisionEngine
from worker.inference.fake_engine import FakeInferenceEngine

_ENGINES: dict[str, type[InferenceEngine]] = {}


def register_engine(name: str, engine_class: type[InferenceEngine]) -> None:
    """Registra uma classe de motor de inferencia sob um nome."""
    _ENGINES[name] = engine_class


def get_engine_class(name: str) -> type[InferenceEngine] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _ENGINES.get(name)


def available_engines() -> list[str]:
    """Nomes de todos os motores registrados no momento."""
    return sorted(_ENGINES)


register_engine("fake", FakeInferenceEngine)
register_engine("basic_vision", BasicVisionEngine)
