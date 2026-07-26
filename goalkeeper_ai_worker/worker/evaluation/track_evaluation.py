"""TrackEvaluation: avaliação estrutural de COMO a decisão de UM
track_id foi produzida (Sprint W39).

Não copia `winning_criteria`/`selected_plan_id`/`discarded_plan_ids`
de `TrackDecision` - quem precisar do detalhe bruto lê `DecisionSet`
pela mesma chave `track_id` (decisão aprovada: evitar duplicar campo já
acessível em outro artefato, mesmo erro corrigido na W38)."""
from __future__ import annotations

from dataclasses import dataclass

from worker.evaluation.resolution_method import ResolutionMethod


@dataclass(frozen=True)
class TrackEvaluation:
    track_id: int
    resolution_method: ResolutionMethod

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "resolution_method": self.resolution_method.value,
        }
