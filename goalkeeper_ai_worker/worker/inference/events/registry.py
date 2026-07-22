"""Registry de SceneAnalyzers - guarda quais classes de SceneAnalyzer
estão disponíveis, por nome.

Especialização do Plugin Registry (AI_WORKER_CONSTITUTION.md, Seção 6)
para a família de Eventos de Cena - paralela ao Registry de motores, de
Processors, de Detectors e de Trackers, cada um independente. Adicionar
um SceneAnalyzer novo: escrever uma classe que implementa `SceneAnalyzer`
(base.py) e chamar `register_analyzer` com ela - nenhuma mudança em
`SceneAnalysisProcessor`, `factory.py` ou no restante do Worker."""
from __future__ import annotations

from worker.inference.events.base import SceneAnalyzer
from worker.inference.events.scene_analyzer import BasicSceneAnalyzer

_ANALYZERS: dict[str, type[SceneAnalyzer]] = {}


def register_analyzer(name: str, analyzer_class: type[SceneAnalyzer]) -> None:
    """Registra uma classe de SceneAnalyzer sob um nome."""
    _ANALYZERS[name] = analyzer_class


def get_analyzer_class(name: str) -> type[SceneAnalyzer] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _ANALYZERS.get(name)


def available_analyzers() -> list[str]:
    """Nomes de todos os SceneAnalyzers registrados no momento."""
    return sorted(_ANALYZERS)


register_analyzer("basic", BasicSceneAnalyzer)
