"""Testes de worker.timeline.enrichment.provenance.Provenance."""
from __future__ import annotations

import dataclasses

import pytest

from worker.timeline.enrichment.provenance import Provenance


def test_primary_parent_id_with_single_source():
    provenance = Provenance(source_event_ids=("e1",))
    assert provenance.primary_parent_id == "e1"


def test_primary_parent_id_with_multiple_sources_returns_the_first():
    provenance = Provenance(source_event_ids=("e1", "e2", "e3"))
    assert provenance.primary_parent_id == "e1"


def test_primary_parent_id_is_none_when_empty():
    provenance = Provenance(source_event_ids=())
    assert provenance.primary_parent_id is None


def test_is_frozen_immutable():
    provenance = Provenance(source_event_ids=("e1",))
    with pytest.raises(dataclasses.FrozenInstanceError):
        provenance.source_event_ids = ("e2",)  # type: ignore[misc]
