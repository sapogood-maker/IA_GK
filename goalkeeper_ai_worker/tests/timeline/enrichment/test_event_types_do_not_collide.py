"""Confirma que nenhuma constante de worker.timeline.enrichment.event_types
(tipos DERIVADOS, Sprint W31) colide, por VALOR, com uma constante ja
existente em worker.timeline.event_types (tipos base, Sprint W28) -
risco explicito documentado no arquitetural da W31."""
from __future__ import annotations

from worker.timeline import event_types as base_event_types
from worker.timeline.enrichment import event_types as enrichment_event_types


def _string_constants(module) -> set[str]:
    return {value for name, value in vars(module).items() if not name.startswith("_") and isinstance(value, str)}


def test_no_overlap_between_base_and_derived_event_type_values():
    base_values = _string_constants(base_event_types)
    derived_values = _string_constants(enrichment_event_types)

    overlap = base_values & derived_values
    assert overlap == set(), f"Valores colidindo entre base e derivado: {overlap}"


def test_both_modules_actually_declare_constants():
    """Guarda contra a asserção anterior passar so porque um dos modulos
    esta vazio (falso positivo)."""
    assert len(_string_constants(base_event_types)) > 0
    assert len(_string_constants(enrichment_event_types)) > 0
