"""Confirma que EntityCorrelationEnricher (Nivel 2) e so interface -
nao implementado nesta sprint, por decisao explicita."""
from __future__ import annotations

import pytest

from worker.timeline.enrichment.enrichers.entity_correlation import EntityCorrelationEnricher


def test_enrich_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        EntityCorrelationEnricher().enrich([])


def test_is_registered_for_discovery_but_not_usable():
    from worker.timeline.enrichment.registry import available_enrichers

    assert "entity_correlation" in available_enrichers()
