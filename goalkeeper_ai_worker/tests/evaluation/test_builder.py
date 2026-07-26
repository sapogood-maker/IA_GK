"""Testes de worker.evaluation.builder.evaluate - o essencial da
Sprint W39, incluindo o teste de regressao que roda decide() (W37) de
verdade para provar que as strings replicadas ainda batem."""
from __future__ import annotations

from worker.decision.builder import decide
from worker.decision.decision_set import DecisionSet
from worker.decision.entity_decision import EntityDecision
from worker.decision.track_decision import TrackDecision
from worker.evaluation.builder import evaluate
from worker.evaluation.resolution_method import ResolutionMethod
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan


def _track_decision(track_id: int, winning_criteria: tuple[str, ...]) -> TrackDecision:
    return TrackDecision(
        track_id=track_id,
        selected_plan_id=f"engage:track:{track_id}",
        plan_type=PlanType.ENGAGE,
        winning_criteria=winning_criteria,
        discarded_plan_ids=(),
    )


def _entity_decision(entity: str, winning_criteria: tuple[str, ...]) -> EntityDecision:
    return EntityDecision(
        entity=entity,
        selected_plan_id=f"disengage:entity:{entity}",
        plan_type=PlanType.DISENGAGE,
        winning_criteria=winning_criteria,
        discarded_plan_ids=(),
    )


def test_empty_decision_set_produces_empty_evaluation_set():
    result = evaluate(DecisionSet())
    assert result.track_evaluations == {}
    assert result.entity_evaluations == {}


def test_single_candidate_maps_to_single_candidate():
    decision_set = DecisionSet(track_decisions={1: _track_decision(1, ("only_candidate",))})
    result = evaluate(decision_set)
    assert result.track_evaluations[1].resolution_method == ResolutionMethod.SINGLE_CANDIDATE


def test_structural_criterion_alone_maps_to_structural_criterion():
    decision_set = DecisionSet(track_decisions={1: _track_decision(1, ("more_satisfied_preconditions",))})
    result = evaluate(decision_set)
    assert result.track_evaluations[1].resolution_method == ResolutionMethod.STRUCTURAL_CRITERION


def test_tiebreak_alone_maps_to_deterministic_tiebreak():
    decision_set = DecisionSet(track_decisions={1: _track_decision(1, ("deterministic_tiebreak_by_plan_id",))})
    result = evaluate(decision_set)
    assert result.track_evaluations[1].resolution_method == ResolutionMethod.DETERMINISTIC_TIEBREAK


def test_structural_criterion_combined_with_tiebreak_still_maps_to_tiebreak():
    decision_set = DecisionSet(
        track_decisions={
            1: _track_decision(1, ("more_satisfied_preconditions", "deterministic_tiebreak_by_plan_id"))
        }
    )
    result = evaluate(decision_set)
    assert result.track_evaluations[1].resolution_method == ResolutionMethod.DETERMINISTIC_TIEBREAK


def test_entity_evaluations_follow_the_same_logic():
    decision_set = DecisionSet(entity_decisions={"ball": _entity_decision("ball", ("only_candidate",))})
    result = evaluate(decision_set)
    assert result.entity_evaluations["ball"].resolution_method == ResolutionMethod.SINGLE_CANDIDATE


def test_determinism_same_decision_set_produces_same_evaluation_set():
    decision_set = DecisionSet(track_decisions={1: _track_decision(1, ("only_candidate",))})
    first = evaluate(decision_set).to_dict()
    second = evaluate(decision_set).to_dict()
    assert first == second


def test_to_dict_serialization_with_multiple_evaluations():
    decision_set = DecisionSet(
        track_decisions={
            3: _track_decision(3, ("only_candidate",)),
            1: _track_decision(1, ("only_candidate",)),
        }
    )
    payload = evaluate(decision_set).to_dict()
    assert list(payload["track_evaluations"].keys()) == [1, 3]


def _plan(plan_id: str, track_id: int, plan_type: PlanType) -> TrackPlan:
    return TrackPlan(
        plan_id=plan_id,
        plan_type=plan_type,
        track_id=track_id,
        origin_conviction_id=f"{plan_type.value}:track:{track_id}",
        satisfied_preconditions=("conviction_level_at_least_stable",),
        state=PlanState.ONGOING,
        objective="...",
    )


def test_regression_real_decide_output_still_classifies_as_deterministic_tiebreak():
    """Roda o decide() real (W37) sobre um PlanningSet desenhado para
    empatar totalmente (mesma fixture de tests/decision/test_builder.py)
    - prova que as strings replicadas em worker/evaluation/builder.py
    ainda batem com o comportamento real de worker/decision/builder.py,
    sem importar nada de la."""
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": _plan("engage:track:1", 1, PlanType.ENGAGE),
            "reacquire:track:1": _plan("reacquire:track:1", 1, PlanType.REACQUIRE),
        }
    )
    decision_set = decide(planning_set)
    assert decision_set.track_decisions[1].winning_criteria == ("deterministic_tiebreak_by_plan_id",)

    evaluation_set = evaluate(decision_set)
    assert evaluation_set.track_evaluations[1].resolution_method == ResolutionMethod.DETERMINISTIC_TIEBREAK


def test_regression_real_decide_output_still_classifies_as_single_candidate():
    planning_set = PlanningSet(track_plans={"engage:track:1": _plan("engage:track:1", 1, PlanType.ENGAGE)})
    decision_set = decide(planning_set)
    evaluation_set = evaluate(decision_set)
    assert evaluation_set.track_evaluations[1].resolution_method == ResolutionMethod.SINGLE_CANDIDATE
