"""EvaluationSet: raiz do conjunto de avaliações estruturais (Sprint
W39) - um por chamada de `evaluate`.

Sem estatísticas agregadas (ex.: contagem total de decisões resolvidas
por fallback) - deliberadamente omitido, trivialmente derivável por
qualquer consumidor iterando os dicts, mesma disciplina de todas as
camadas anteriores.

Garantia de junção total (decisão arquitetural da Sprint W40):
`track_evaluations`/`entity_evaluations` sempre compartilham
exatamente o mesmo conjunto de chaves que
`DecisionSet.track_decisions`/`entity_decisions` - `evaluate()` produz
uma avaliação para cada decisão, sem filtrar nenhuma. Por isso não
existe (nem se justifica) uma camada de "Explainability" separada:
quem precisar explicar uma decisão (o que foi decidido, por quê, como,
qual mecanismo resolveu o vencedor) já responde tudo isso lendo
`DecisionSet` e `EvaluationSet` pela mesma chave `track_id`/`entity` -
o cruzamento é sempre total e seguro, nunca há chave órfã de um lado
sem o outro."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.evaluation.entity_evaluation import EntityEvaluation
from worker.evaluation.track_evaluation import TrackEvaluation


@dataclass(frozen=True)
class EvaluationSet:
    track_evaluations: dict[int, TrackEvaluation] = field(default_factory=dict)
    entity_evaluations: dict[str, EntityEvaluation] = field(default_factory=dict)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None

    def to_dict(self) -> dict:
        return {
            "track_evaluations": {
                track_id: self.track_evaluations[track_id].to_dict() for track_id in sorted(self.track_evaluations)
            },
            "entity_evaluations": {
                entity: self.entity_evaluations[entity].to_dict() for entity in sorted(self.entity_evaluations)
            },
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
        }
