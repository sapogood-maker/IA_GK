"""build_plans: projeta um PlanningSet a partir de um ConvictionSet já
construído (Sprint W36).

Função pura e sem memória própria - todo o "estado do plano" é derivado
do snapshot ATUAL de `ConvictionSet` (que já contém a informação
temporal computada pela Conviction Layer, W35): `conviction.state`,
`conviction.level` e `conviction.consecutive_observations`/
`lifetime_observations`. Nenhum `PlanningSet` anterior é lido ou
necessário. O(número de convicções de track + de entidade) - nunca
volta a `HypothesisSet`, `WorkingState`, `TemporalMemory`, `Timeline`
ou `Event`.

Nunca importa `worker.hypothesis` - as strings de `hypothesis_type`
usadas para decidir o `PlanType` são REPLICADAS localmente (mesma
disciplina de `worker/memory/content_events.py`, W32), nunca o Enum
`HypothesisType` importado (documento arquitetural da W36, Seções 3/6).
"""
from __future__ import annotations

from worker.conviction.conviction_level import ConvictionLevel, level_for
from worker.conviction.conviction_set import ConvictionSet
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.entity_conviction import EntityConviction
from worker.conviction.track_conviction import TrackConviction
from worker.planning.entity_plan import EntityPlan
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan

# Strings replicadas de HypothesisType.value (W34) - nunca importadas.
# Divida arquitetural conhecida (documento W36, Secao 14, risco 4):
# testada contra os valores reais em tests/planning/test_builder.py.
_STATIONARY = "stationary"
_MOVEMENT = "movement"
_RECOVERY = "recovery"
_VISIBILITY = "visibility"

# Mapeamento 1:1 - escolha de implementacao desta sprint, nao um
# contrato permanente (Secao 6 do documento). Mudar aqui nunca exige
# alterar worker/hypothesis/ ou worker/conviction/.
_PLAN_TYPE_FOR_HYPOTHESIS_TYPE = {
    _STATIONARY: PlanType.ENGAGE,
    _MOVEMENT: PlanType.PURSUE,
    _RECOVERY: PlanType.REACQUIRE,
    _VISIBILITY: PlanType.DISENGAGE,
}

# Replica _STABLE_THRESHOLD de worker.conviction.conviction_level (nao
# importada - e privada la) - testada contra o valor real.
_MIN_LIFETIME_FOR_INVALIDATION = 3

_SATISFYING_LEVELS = (ConvictionLevel.STABLE, ConvictionLevel.STRONG)

_OBJECTIVE_TEMPLATES = {
    PlanType.ENGAGE: "Um plano de engajamento passa a ser possível para {subject}.",
    PlanType.PURSUE: "Um plano de perseguição passa a ser possível para {subject}.",
    PlanType.REACQUIRE: "Um plano de reaquisição de identidade passa a ser possível para {subject}.",
    PlanType.DISENGAGE: "Um plano de desengajamento passa a ser possível para {subject}.",
}


def build_plans(conviction_set: ConvictionSet) -> PlanningSet:
    track_plans: dict[str, TrackPlan] = {}
    for hid in sorted(conviction_set.track_convictions):
        plan = _plan_for_track_conviction(conviction_set.track_convictions[hid])
        if plan is not None:
            track_plans[plan.plan_id] = plan

    entity_plans: dict[str, EntityPlan] = {}
    for hid in sorted(conviction_set.entity_convictions):
        plan = _plan_for_entity_conviction(conviction_set.entity_convictions[hid])
        if plan is not None:
            entity_plans[plan.plan_id] = plan

    return PlanningSet(
        track_plans=track_plans,
        entity_plans=entity_plans,
        observed_at_frame=conviction_set.observed_at_frame,
        observed_at_timestamp=conviction_set.observed_at_timestamp,
    )


def _is_satisfying(level: ConvictionLevel) -> bool:
    return level in _SATISFYING_LEVELS


def _just_crossed_into_satisfying(consecutive_observations: int, state: ConvictionState) -> bool:
    if state != ConvictionState.STRENGTHENED:
        return False
    if consecutive_observations <= 1:
        return True  # defensivo - STRENGTHENED nao ocorre com consecutive<=1 na pratica (W35)
    previous_level = level_for(consecutive_observations - 1)
    return not _is_satisfying(previous_level)


def _plan_state_for(state: ConvictionState, level: ConvictionLevel, consecutive_observations: int, lifetime_observations: int) -> PlanState | None:
    if state == ConvictionState.WEAKENED:
        if lifetime_observations >= _MIN_LIFETIME_FOR_INVALIDATION:
            return PlanState.INVALIDATED
        return None
    if not _is_satisfying(level):
        return None
    if _just_crossed_into_satisfying(consecutive_observations, state):
        return PlanState.EMERGED
    return PlanState.ONGOING


def _preconditions_for(plan_state: PlanState) -> tuple[str, ...]:
    if plan_state == PlanState.INVALIDATED:
        return ("conviction_previously_stable_now_weakened",)
    return ("conviction_level_at_least_stable",)


def _plan_for_track_conviction(conviction: TrackConviction) -> TrackPlan | None:
    plan_type = _PLAN_TYPE_FOR_HYPOTHESIS_TYPE.get(conviction.hypothesis_type.value)
    if plan_type is None:
        return None
    plan_state = _plan_state_for(
        conviction.state, conviction.level, conviction.consecutive_observations, conviction.lifetime_observations
    )
    if plan_state is None:
        return None

    return TrackPlan(
        plan_id=f"{plan_type.value}:track:{conviction.track_id}",
        plan_type=plan_type,
        track_id=conviction.track_id,
        origin_conviction_id=conviction.hypothesis_id,
        satisfied_preconditions=_preconditions_for(plan_state),
        state=plan_state,
        objective=_OBJECTIVE_TEMPLATES[plan_type].format(subject=f"o track {conviction.track_id}"),
    )


def _plan_for_entity_conviction(conviction: EntityConviction) -> EntityPlan | None:
    plan_type = _PLAN_TYPE_FOR_HYPOTHESIS_TYPE.get(conviction.hypothesis_type.value)
    if plan_type is None:
        return None
    plan_state = _plan_state_for(
        conviction.state, conviction.level, conviction.consecutive_observations, conviction.lifetime_observations
    )
    if plan_state is None:
        return None

    return EntityPlan(
        plan_id=f"{plan_type.value}:entity:{conviction.entity}",
        plan_type=plan_type,
        entity=conviction.entity,
        origin_conviction_id=conviction.hypothesis_id,
        satisfied_preconditions=_preconditions_for(plan_state),
        state=plan_state,
        objective=_OBJECTIVE_TEMPLATES[plan_type].format(subject=f"a entidade '{conviction.entity}'"),
    )
