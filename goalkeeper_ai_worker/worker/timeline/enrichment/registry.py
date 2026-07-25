"""Registry de Enricher - guarda quais classes estao disponiveis, por
nome. Mesmo padrao de worker/segments/registry.py (por sua vez espelho
de worker/inference/detectors/registry.py): adicionar um Enricher novo -
escrever uma classe que implementa `Enricher` e chamar `register_enricher`
- nenhuma mudanca em `EnrichmentPipeline`/`factory.py`.

`entity_correlation` (Nivel 2) e registrado para fins de descoberta
(`available_enrichers()` lista que ele existe), mas chamar `.enrich()`
nele levanta `NotImplementedError` de proposito - ver enrichers/
entity_correlation.py."""
from __future__ import annotations

from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.enrichers.entity_correlation import EntityCorrelationEnricher
from worker.timeline.enrichment.enrichers.motion_transitions import MotionTransitionEnricher
from worker.timeline.enrichment.enrichers.track_recovery import TrackRecoveryConfidenceEnricher
from worker.timeline.enrichment.enrichers.track_stability import TrackStabilityEnricher

_ENRICHERS: dict[str, type[Enricher]] = {}


def register_enricher(name: str, enricher_class: type[Enricher]) -> None:
    """Registra uma classe de Enricher sob um nome."""
    _ENRICHERS[name] = enricher_class


def get_enricher_class(name: str) -> type[Enricher] | None:
    """Devolve a classe registrada sob `name`, ou None se desconhecida."""
    return _ENRICHERS.get(name)


def available_enrichers() -> list[str]:
    """Nomes de todos os Enrichers registrados no momento."""
    return sorted(_ENRICHERS)


register_enricher("motion_transitions", MotionTransitionEnricher)
register_enricher("track_stability", TrackStabilityEnricher)
register_enricher("track_recovery", TrackRecoveryConfidenceEnricher)
register_enricher("entity_correlation", EntityCorrelationEnricher)
