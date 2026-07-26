"""EntityEvaluation: avaliação estrutural de COMO a decisão de UMA
entidade foi produzida (Sprint W39).

Irmã de `TrackEvaluation`, não subclasse - mesma decisão de W33-W37
para os pares Track/Entity anteriores."""
from __future__ import annotations

from dataclasses import dataclass

from worker.evaluation.resolution_method import ResolutionMethod


@dataclass(frozen=True)
class EntityEvaluation:
    entity: str
    resolution_method: ResolutionMethod

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "resolution_method": self.resolution_method.value,
        }
