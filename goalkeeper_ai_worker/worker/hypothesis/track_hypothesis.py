"""TrackHypothesis: uma possibilidade sobre UM track_id (Sprint W34).

Nunca afirma que algo é verdadeiro - `description` é sempre linguagem de
possibilidade ("aparenta", "pode haver", "sugere"). `support` é uma
contagem inteira de `matching_conditions` - NUNCA uma confiança/
probabilidade (isso pertence a uma futura Conviction Layer)."""
from __future__ import annotations

from dataclasses import dataclass

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType


@dataclass(frozen=True)
class TrackHypothesis:
    hypothesis_id: str
    hypothesis_type: HypothesisType
    track_id: int
    description: str
    evidence: tuple[Evidence, ...]
    matching_conditions: tuple[str, ...]
    support: int
    origin: str  # identificador estavel do conceito (ex. "stationary"), nunca nome de funcao

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type.value,
            "track_id": self.track_id,
            "description": self.description,
            "evidence": [item.to_dict() for item in self.evidence],
            "matching_conditions": list(self.matching_conditions),
            "support": self.support,
            "origin": self.origin,
        }
