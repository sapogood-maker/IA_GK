"""Provenance: rastreia TODOS os eventos de origem de um evento derivado
(Sprint W31, ajuste arquitetural aprovado).

`Event.parent_event_id` (W28) aceita so UM id - schema intocado nesta
sprint. Todo Enricher desta sprint usa `Provenance` para montar o evento
derivado: `primary_parent_id` vira `Event.parent_event_id` (compatibilidade
com o schema de hoje), e a lista COMPLETA de `source_event_ids` vai para
`Event.metadata["provenance"]` - nenhuma informacao de proveniencia
multipla se perde, mesmo hoje. Promover `provenance` a campo de primeira
classe de `Event` (em vez de viver em `metadata`) e decisao explicita de
uma sprint futura, quando um Enricher precisar de verdade de mais de uma
origem em cadeias mais longas - `TrackRecoveryConfidenceEnricher`
(enrichers/track_recovery.py) ja usa 2 origens hoje, prova de que a
estrutura funciona sem exigir essa migracao agora.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    """Sequencia ordenada e imutavel de `event_id`s de origem."""

    source_event_ids: tuple[str, ...]

    @property
    def primary_parent_id(self) -> str | None:
        """Ponte de compatibilidade com `Event.parent_event_id` (so aceita
        1) - o primeiro id da proveniencia, ou None se vazia."""
        return self.source_event_ids[0] if self.source_event_ids else None
