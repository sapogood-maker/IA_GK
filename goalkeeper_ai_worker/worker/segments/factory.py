"""Ponto unico de resolucao da SegmentStrategy ativa, a partir de um
nome - nunca hardcoded em PlaySegmenter ou no CLI.

Espelha worker/inference/detectors/factory.py (create_detector) para a
familia de SegmentStrategy. Diferente de Detector/Tracker (que sempre
recebem `WorkerSettings`), uma SegmentStrategy ainda nao e configurada
por variavel de ambiente (Sprint W30 nao integra ao pipeline/Settings) -
os parametros de cada estrategia (ex.: `max_gap_seconds` da GapStrategy)
sao passados diretamente como kwargs."""
from __future__ import annotations

from worker.segments.registry import available_strategies, get_strategy_class
from worker.segments.strategy import SegmentStrategy


class SegmentStrategyError(Exception):
    """Nome de estrategia desconhecido, ou falha ao instanciar uma
    estrategia registrada."""


def create_strategy(name: str, **params) -> SegmentStrategy:
    """Instancia a SegmentStrategy correspondente a `name`.

    Levanta SegmentStrategyError se `name` nao estiver registrado, ou se
    a propria instanciacao falhar (ex.: kwarg invalido para aquela
    estrategia) - nunca faz fallback silencioso para outra estrategia."""
    strategy_class = get_strategy_class(name)
    if strategy_class is None:
        raise SegmentStrategyError(
            f"SegmentStrategy desconhecida: '{name}'. Disponiveis: {', '.join(available_strategies())}"
        )
    try:
        return strategy_class(**params)
    except SegmentStrategyError:
        raise
    except Exception as exc:
        raise SegmentStrategyError(f"Falha ao instanciar a SegmentStrategy '{name}': {exc}") from exc
