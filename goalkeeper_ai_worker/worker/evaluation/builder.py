"""evaluate: projeta um EvaluationSet a partir de um DecisionSet já
construído (Sprint W39).

Função pura, sem estado interno, sem cache, sem efeito colateral - um
único argumento, `DecisionSet` (W37/W38). Nunca volta a `PlanningSet`,
`ConvictionSet`, `HypothesisSet`, `WorkingState`, `TemporalMemory`,
`Timeline` ou `Event`. Nunca modifica `DecisionSet` - só lê.

As strings de `winning_criteria` são REPLICADAS de
`worker/decision/builder.py` (W37), nunca importadas - nem sequer são
constantes nomeadas lá hoje (literais soltos dentro da função), então
esta é uma réplica mais frágil que o padrão usual de W32/W36. Protegida
por um teste de regressão que roda `decide()` de verdade (ver
tests/evaluation/test_builder.py)."""
from __future__ import annotations

from worker.decision.decision_set import DecisionSet
from worker.decision.entity_decision import EntityDecision
from worker.decision.track_decision import TrackDecision
from worker.evaluation.entity_evaluation import EntityEvaluation
from worker.evaluation.evaluation_set import EvaluationSet
from worker.evaluation.resolution_method import ResolutionMethod
from worker.evaluation.track_evaluation import TrackEvaluation

_STRUCTURAL_CRITERION = "more_satisfied_preconditions"
_TIEBREAK_CRITERION = "deterministic_tiebreak_by_plan_id"


def evaluate(decision_set: DecisionSet) -> EvaluationSet:
    track_evaluations = {
        track_id: _evaluate_track(track_id, decision)
        for track_id, decision in decision_set.track_decisions.items()
    }
    entity_evaluations = {
        entity: _evaluate_entity(entity, decision)
        for entity, decision in decision_set.entity_decisions.items()
    }
    return EvaluationSet(
        track_evaluations=track_evaluations,
        entity_evaluations=entity_evaluations,
        observed_at_frame=decision_set.observed_at_frame,
        observed_at_timestamp=decision_set.observed_at_timestamp,
    )


def _resolution_method_for(winning_criteria: tuple[str, ...]) -> ResolutionMethod:
    # Se o desempate alfabetico foi necessario, ele e o fator que
    # efetivamente decidiu - mesmo que more_satisfied_preconditions
    # tambem esteja presente (filtrou parte dos candidatos, mas nao
    # decidiu sozinho).
    if _TIEBREAK_CRITERION in winning_criteria:
        return ResolutionMethod.DETERMINISTIC_TIEBREAK
    if _STRUCTURAL_CRITERION in winning_criteria:
        return ResolutionMethod.STRUCTURAL_CRITERION
    return ResolutionMethod.SINGLE_CANDIDATE


def _evaluate_track(track_id: int, decision: TrackDecision) -> TrackEvaluation:
    return TrackEvaluation(track_id=track_id, resolution_method=_resolution_method_for(decision.winning_criteria))


def _evaluate_entity(entity: str, decision: EntityDecision) -> EntityEvaluation:
    return EntityEvaluation(entity=entity, resolution_method=_resolution_method_for(decision.winning_criteria))
