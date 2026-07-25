"""Testes de worker.timeline.enrichment.factory.create_enricher."""
from __future__ import annotations

import pytest

from worker.timeline.enrichment.enrichers.motion_transitions import MotionTransitionEnricher
from worker.timeline.enrichment.factory import EnricherError, create_enricher


def test_creates_registered_enricher_by_name():
    enricher = create_enricher("motion_transitions")
    assert isinstance(enricher, MotionTransitionEnricher)


def test_passes_through_kwargs_to_the_constructor():
    enricher = create_enricher("motion_transitions", entity_filter="ball", min_stationary_seconds=3.0)
    assert enricher._entity_filter == "ball"
    assert enricher._min_stationary_seconds == 3.0


def test_unknown_name_raises_enricher_error():
    with pytest.raises(EnricherError, match="desconhecido"):
        create_enricher("does-not-exist")


def test_invalid_kwarg_raises_enricher_error_not_a_raw_typeerror():
    with pytest.raises(EnricherError):
        create_enricher("motion_transitions", nonexistent_param=True)
