"""Ponto unico de resolucao do Enricher ativo, a partir de um nome -
nunca hardcoded em EnrichmentPipeline ou em quem o invoca.

Espelha worker/segments/factory.py (create_strategy) para a familia de
Enricher."""
from __future__ import annotations

from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.registry import available_enrichers, get_enricher_class


class EnricherError(Exception):
    """Nome de Enricher desconhecido, ou falha ao instanciar um Enricher
    registrado."""


def create_enricher(name: str, **params) -> Enricher:
    """Instancia o Enricher correspondente a `name`.

    Levanta EnricherError se `name` nao estiver registrado, ou se a
    propria instanciacao falhar - nunca faz fallback silencioso para
    outro Enricher."""
    enricher_class = get_enricher_class(name)
    if enricher_class is None:
        raise EnricherError(f"Enricher desconhecido: '{name}'. Disponiveis: {', '.join(available_enrichers())}")
    try:
        return enricher_class(**params)
    except EnricherError:
        raise
    except Exception as exc:
        raise EnricherError(f"Falha ao instanciar o Enricher '{name}': {exc}") from exc
