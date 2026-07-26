"""Testes de worker.decision.builder.decide - o essencial da Sprint
W37: decisao trivial, ausencia sem candidato valido, desempate por
precondicoes estruturais, desempate deterministico final,
discarded_plan_ids, independencia entre sujeitos, determinismo,
serializacao."""
from __future__ import annotations

from worker.decision.builder import decide
from worker.planning.entity_plan import EntityPlan
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan


def _track_plan(plan_id: str, track_id: int, plan_type: PlanType, state=PlanState.ONGOING, num_preconditions=1) -> TrackPlan:
    return TrackPlan(
        plan_id=plan_id,
        plan_type=plan_type,
        track_id=track_id,
        origin_conviction_id=f"{plan_type.value}:track:{track_id}",
        satisfied_preconditions=tuple(f"cond_{i}" for i in range(num_preconditions)),
        state=state,
        objective="...",
    )


def _entity_plan(plan_id: str, entity: str, plan_type: PlanType, state=PlanState.ONGOING, num_preconditions=1) -> EntityPlan:
    return EntityPlan(
        plan_id=plan_id,
        plan_type=plan_type,
        entity=entity,
        origin_conviction_id=f"visibility:entity:{entity}",
        satisfied_preconditions=tuple(f"cond_{i}" for i in range(num_preconditions)),
        state=state,
        objective="...",
    )


def test_empty_planning_set_produces_empty_decision_set():
    result = decide(PlanningSet())
    assert result.track_decisions == {}
    assert result.entity_decisions == {}


def test_trivial_decision_with_single_candidate():
    planning_set = PlanningSet(track_plans={"engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE)})
    result = decide(planning_set)
    decision = result.track_decisions[1]
    assert decision.selected_plan_id == "engage:track:1"
    assert decision.winning_criteria == ("only_candidate",)
    assert decision.discarded_plan_ids == ()


def test_no_decision_when_only_plan_is_invalidated():
    planning_set = PlanningSet(
        track_plans={"engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE, state=PlanState.INVALIDATED)}
    )
    result = decide(planning_set)
    assert 1 not in result.track_decisions


def test_no_decision_when_no_plans_for_track():
    result = decide(PlanningSet())
    assert result.track_decisions == {}


def test_tiebreak_by_more_satisfied_preconditions():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE, num_preconditions=1),
            "reacquire:track:1": _track_plan("reacquire:track:1", 1, PlanType.REACQUIRE, num_preconditions=2),
        }
    )
    decision = decide(planning_set).track_decisions[1]
    assert decision.selected_plan_id == "reacquire:track:1"
    assert decision.winning_criteria == ("more_satisfied_preconditions",)
    assert decision.discarded_plan_ids == ("engage:track:1",)


def test_deterministic_tiebreak_by_plan_id_when_fully_tied():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE, num_preconditions=1),
            "reacquire:track:1": _track_plan("reacquire:track:1", 1, PlanType.REACQUIRE, num_preconditions=1),
        }
    )
    decision = decide(planning_set).track_decisions[1]
    assert decision.selected_plan_id == "engage:track:1"  # "engage" < "reacquire" lexicograficamente
    assert decision.winning_criteria == ("deterministic_tiebreak_by_plan_id",)
    assert decision.discarded_plan_ids == ("reacquire:track:1",)


def test_never_selects_an_invalidated_plan_even_if_others_are_worse():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE, state=PlanState.INVALIDATED, num_preconditions=5),
            "pursue:track:1": _track_plan("pursue:track:1", 1, PlanType.PURSUE, state=PlanState.ONGOING, num_preconditions=1),
        }
    )
    decision = decide(planning_set).track_decisions[1]
    assert decision.selected_plan_id == "pursue:track:1"
    assert decision.discarded_plan_ids == ()  # o invalidado nunca foi "candidato"


def test_independence_between_subjects():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE),
            "pursue:track:2": _track_plan("pursue:track:2", 2, PlanType.PURSUE),
        }
    )
    result = decide(planning_set)
    assert result.track_decisions[1].selected_plan_id == "engage:track:1"
    assert result.track_decisions[2].selected_plan_id == "pursue:track:2"


def test_entity_decisions_follow_the_same_logic():
    planning_set = PlanningSet(
        entity_plans={"disengage:entity:ball": _entity_plan("disengage:entity:ball", "ball", PlanType.DISENGAGE)}
    )
    result = decide(planning_set)
    decision = result.entity_decisions["ball"]
    assert decision.selected_plan_id == "disengage:entity:ball"
    assert decision.winning_criteria == ("only_candidate",)


def test_determinism_same_planning_set_produces_same_decision_set():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE),
            "reacquire:track:1": _track_plan("reacquire:track:1", 1, PlanType.REACQUIRE),
        }
    )
    first = decide(planning_set).to_dict()
    second = decide(planning_set).to_dict()
    assert first == second


def test_to_dict_serialization_with_multiple_decisions():
    planning_set = PlanningSet(
        track_plans={
            "engage:track:3": _track_plan("engage:track:3", 3, PlanType.ENGAGE),
            "engage:track:1": _track_plan("engage:track:1", 1, PlanType.ENGAGE),
        }
    )
    payload = decide(planning_set).to_dict()
    assert list(payload["track_decisions"].keys()) == [1, 3]
