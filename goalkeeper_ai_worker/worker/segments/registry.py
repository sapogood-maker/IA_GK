"""Registry de SegmentStrategy - guarda quais classes de estrategia estao
disponiveis, por nome.

Mesmo padrao de worker/inference/detectors/registry.py (e dos registries
irmaos de Tracker/SceneAnalyzer/WorldModel/Analyzer): adicionar uma
estrategia nova (ex.: continuidade de track, continuidade da bola,
composta) - escrever uma classe que implementa `SegmentStrategy`
(strategy.py) e chamar `register_strategy` - nenhuma mudanca em
`PlaySegmenter`, `factory.py` ou no restante do Worker."""
from __future__ import annotations

from worker.segments.gap_strategy import GapStrategy
from worker.segments.strategy import SegmentStrategy

_STRATEGIES: dict[str, type[SegmentStrategy]] = {}


def register_strategy(name: str, strategy_class: type[SegmentStrategy]) -> None:
    """Registra uma classe de SegmentStrategy sob um nome."""
    _STRATEGIES[name] = strategy_class


def get_strategy_class(name: str) -> type[SegmentStrategy] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _STRATEGIES.get(name)


def available_strategies() -> list[str]:
    """Nomes de todas as SegmentStrategy registradas no momento."""
    return sorted(_STRATEGIES)


register_strategy("gap", GapStrategy)
