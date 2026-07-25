"""EntityHypothesis: uma possibilidade sobre UMA entidade (rótulo
normalizado, ex. "ball") - Sprint W34.

Irmã de `TrackHypothesis`, não subclasse - mesma decisão de W33 para
`TrackState`/`EntityState` (identificadores de tipos diferentes, nenhum
código precisa tratá-las polimorficamente hoje)."""
from __future__ import annotations

from dataclasses import dataclass

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType


@dataclass(frozen=True)
class EntityHypothesis:
    hypothesis_id: str
    hypothesis_type: HypothesisType
    entity: str
    description: str
    evidence: tuple[Evidence, ...]
    matching_conditions: tuple[str, ...]
    support: int
    origin: str

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type.value,
            "entity": self.entity,
            "description": self.description,
            "evidence": [item.to_dict() for item in self.evidence],
            "matching_conditions": list(self.matching_conditions),
            "support": self.support,
            "origin": self.origin,
        }
