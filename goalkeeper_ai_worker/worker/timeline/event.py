"""Event: unidade atomica e imutavel da Perception Timeline (Sprint W28).

Registra um FATO de percepcao - nunca uma decisao/avaliacao (isso
continua exclusivamente nos Analyzers, camada acima, inalterada por esta
sprint). `frozen=True` e imutabilidade real do Python: depois de criado,
um Event nunca muda - `dataclasses.FrozenInstanceError` se algo tentar
reatribuir um campo. Enriquecimento futuro acontece só criando um NOVO
Event que referencia o original via `parent_event_id`, nunca editando o
existente - a Timeline (`timeline.py`) e Event Sourcing friendly por
causa dessa garantia: reproduzir a sequencia de Events, em ordem, deve
bastar para reconstruir todo estado de percepcao derivado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    """Um fato atomico observado durante o processamento de um video.

    `parent_event_id` fica vazio (None) em todo Event produzido por esta
    sprint - nenhum builder atual tem uma cadeia causal real para
    registrar ainda (isso depende de Play Segmentation/State Machine,
    W29+). O campo existe agora para essas sprints futuras não exigirem
    migração de schema.
    """

    event_type: str
    frame_index: int
    timestamp_seconds: float | None
    track_id: int | None
    entity: str | None
    position: dict | None
    confidence: float | None
    metadata: dict = field(default_factory=dict)
    parent_event_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "frame_index": self.frame_index,
            "timestamp_seconds": self.timestamp_seconds,
            "track_id": self.track_id,
            "entity": self.entity,
            "position": self.position,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "parent_event_id": self.parent_event_id,
        }
