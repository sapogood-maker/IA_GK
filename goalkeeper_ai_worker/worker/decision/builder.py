"""decide: projeta um DecisionSet a partir de um PlanningSet já
construído (Sprint W37).

Função pura, sem estado interno, sem cache, sem efeito colateral - um
único argumento, `PlanningSet` (W36). Nunca volta a `ConvictionSet`,
`HypothesisSet`, `WorkingState`, `TemporalMemory`, `Timeline` ou
`Event`. Decisão é sempre por SUJEITO (track ou entidade) - nunca uma
escolha global cruzando sujeitos diferentes.

Critérios de desempate inteiramente estruturais e determinísticos,
sem nenhum conhecimento sobre o significado semântico de um `PlanType`
(mantém o núcleo cognitivo reutilizável para qualquer domínio futuro):
número de `satisfied_preconditions`, depois ordem lexicográfica de
`plan_id`. `PlanState` é lido só como filtro de candidatura (um plano
`INVALIDATED` nunca compete) - nunca copiado para `TrackDecision`/
`EntityDecision`."""
from __future__ import annotations

from worker.decision.decision_set import DecisionSet
from worker.decision.entity_decision import EntityDecision
from worker.decision.track_decision import TrackDecision
from worker.planning.entity_plan import EntityPlan
from worker.planning.plan_state import PlanState
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan


def decide(planning_set: PlanningSet) -> DecisionSet:
    by_track: dict[int, list[TrackPlan]] = {}
    for plan in planning_set.track_plans.values():
        by_track.setdefault(plan.track_id, []).append(plan)

    track_decisions: dict[int, TrackDecision] = {}
    for track_id in sorted(by_track):
        decision = _decide_for_track(track_id, by_track[track_id])
        if decision is not None:
            track_decisions[track_id] = decision

    by_entity: dict[str, list[EntityPlan]] = {}
    for plan in planning_set.entity_plans.values():
        by_entity.setdefault(plan.entity, []).append(plan)

    entity_decisions: dict[str, EntityDecision] = {}
    for entity in sorted(by_entity):
        decision = _decide_for_entity(entity, by_entity[entity])
        if decision is not None:
            entity_decisions[entity] = decision

    return DecisionSet(
        track_decisions=track_decisions,
        entity_decisions=entity_decisions,
        observed_at_frame=planning_set.observed_at_frame,
        observed_at_timestamp=planning_set.observed_at_timestamp,
    )


def _candidates(plans: list) -> list:
    return [p for p in plans if p.state != PlanState.INVALIDATED]


def _select_winner(candidates: list) -> tuple[object, tuple[str, ...]]:
    if len(candidates) == 1:
        return candidates[0], ("only_candidate",)

    max_preconditions = max(len(p.satisfied_preconditions) for p in candidates)
    top = [p for p in candidates if len(p.satisfied_preconditions) == max_preconditions]

    criteria: list[str] = []
    if len(top) < len(candidates):
        criteria.append("more_satisfied_preconditions")

    if len(top) > 1:
        winner = min(top, key=lambda p: p.plan_id)
        criteria.append("deterministic_tiebreak_by_plan_id")
    else:
        winner = top[0]

    return winner, tuple(criteria)


def _decide_for_track(track_id: int, plans: list[TrackPlan]) -> TrackDecision | None:
    candidates = _candidates(plans)
    if not candidates:
        return None

    winner, criteria = _select_winner(candidates)
    discarded = tuple(sorted(p.plan_id for p in candidates if p.plan_id != winner.plan_id))

    return TrackDecision(
        track_id=track_id,
        selected_plan_id=winner.plan_id,
        plan_type=winner.plan_type,
        winning_criteria=criteria,
        discarded_plan_ids=discarded,
    )


def _decide_for_entity(entity: str, plans: list[EntityPlan]) -> EntityDecision | None:
    candidates = _candidates(plans)
    if not candidates:
        return None

    winner, criteria = _select_winner(candidates)
    discarded = tuple(sorted(p.plan_id for p in candidates if p.plan_id != winner.plan_id))

    return EntityDecision(
        entity=entity,
        selected_plan_id=winner.plan_id,
        plan_type=winner.plan_type,
        winning_criteria=criteria,
        discarded_plan_ids=discarded,
    )
