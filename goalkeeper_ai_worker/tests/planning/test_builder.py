"""Testes de worker.planning.builder.build_plans - o essencial da
Sprint W36: criacao, nao-criacao sem Conviction, coexistencia,
continuidade, invalidacao, remocao/abandono, determinismo,
identificadores, serializacao."""
from __future__ import annotations

from worker.conviction.builder import update_convictions
from worker.conviction.conviction_set import ConvictionSet
from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.planning.builder import (
    _MIN_LIFETIME_FOR_INVALIDATION,
    _MOVEMENT,
    _RECOVERY,
    _STATIONARY,
    _VISIBILITY,
    build_plans,
)
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType


def _track_hyp(hypothesis_type: HypothesisType, track_id: int) -> TrackHypothesis:
    return TrackHypothesis(
        hypothesis_id=f"{hypothesis_type.value}:track:{track_id}",
        hypothesis_type=hypothesis_type,
        track_id=track_id,
        description="...",
        evidence=(Evidence("motion_state", "stopped"),),
        matching_conditions=("motion_state_is_stopped",),
        support=1,
        origin=hypothesis_type.value,
    )


def _entity_hyp(entity: str) -> EntityHypothesis:
    return EntityHypothesis(
        hypothesis_id=f"visibility:entity:{entity}",
        hypothesis_type=HypothesisType.VISIBILITY,
        entity=entity,
        description="...",
        evidence=(Evidence("active_track_ids", "0"),),
        matching_conditions=("no_active_tracks",),
        support=1,
        origin="visibility_entity",
    )


def _hyp_set(track_hyps=(), entity_hyps=(), frame=0, timestamp=0.0) -> HypothesisSet:
    return HypothesisSet(
        track_hypotheses=tuple(track_hyps),
        entity_hypotheses=tuple(entity_hyps),
        observed_at_frame=frame,
        observed_at_timestamp=timestamp,
        source_track_count=1,
    )


def _convictions_after_n_cycles(n, track_hyp_types_by_track, entity_names=()):
    state = ConvictionSet()
    for cycle in range(n):
        track_hyps = [_track_hyp(t, tid) for tid, types in track_hyp_types_by_track.items() for t in types]
        entity_hyps = [_entity_hyp(name) for name in entity_names]
        state = update_convictions(state, _hyp_set(track_hyps, entity_hyps, frame=cycle, timestamp=float(cycle)))
    return state


def test_regression_replicated_hypothesis_type_strings_match_real_enum():
    assert _STATIONARY == HypothesisType.STATIONARY.value
    assert _MOVEMENT == HypothesisType.MOVEMENT.value
    assert _RECOVERY == HypothesisType.RECOVERY.value
    assert _VISIBILITY == HypothesisType.VISIBILITY.value


def test_regression_min_lifetime_matches_conviction_stable_threshold():
    from worker.conviction.conviction_level import ConvictionLevel, level_for

    assert level_for(_MIN_LIFETIME_FOR_INVALIDATION) == ConvictionLevel.STABLE
    assert level_for(_MIN_LIFETIME_FOR_INVALIDATION - 1) != ConvictionLevel.STABLE


def test_empty_conviction_set_produces_empty_planning_set():
    result = build_plans(ConvictionSet())
    assert result.track_plans == {}
    assert result.entity_plans == {}


def test_no_plan_created_while_conviction_is_only_emerging():
    convictions = _convictions_after_n_cycles(2, {1: [HypothesisType.STATIONARY]})  # so 2 ciclos - ainda EMERGING
    result = build_plans(convictions)
    assert result.track_plans == {}


def test_plan_created_when_conviction_reaches_stable():
    convictions = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY]})
    result = build_plans(convictions)
    plan = result.track_plans["engage:track:1"]
    assert plan.plan_type == PlanType.ENGAGE
    assert plan.state == PlanState.EMERGED
    assert plan.origin_conviction_id == "stationary:track:1"


def test_plan_continues_as_ongoing_when_crossing_to_strong():
    convictions = _convictions_after_n_cycles(6, {1: [HypothesisType.STATIONARY]})
    result = build_plans(convictions)
    plan = result.track_plans["engage:track:1"]
    assert plan.state == PlanState.ONGOING  # ja estava satisfatoria desde STABLE (ciclo 3)


def test_coexistence_of_independent_plans():
    convictions = _convictions_after_n_cycles(3, {1: [HypothesisType.MOVEMENT, HypothesisType.VISIBILITY]})
    result = build_plans(convictions)
    assert result.track_plans["pursue:track:1"].plan_type == PlanType.PURSUE
    assert result.track_plans["disengage:track:1"].plan_type == PlanType.DISENGAGE


def test_track_id_1_stationary_and_recovery_coexist():
    convictions = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY, HypothesisType.RECOVERY]})
    result = build_plans(convictions)
    assert "engage:track:1" in result.track_plans
    assert "reacquire:track:1" in result.track_plans


def test_invalidated_after_reaching_stable_then_weakening():
    state = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY]})
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=3, timestamp=3.0))  # WEAKENED
    result = build_plans(state)
    plan = result.track_plans["engage:track:1"]
    assert plan.state == PlanState.INVALIDATED


def test_no_plan_when_weakened_before_ever_reaching_stable():
    state = _convictions_after_n_cycles(1, {1: [HypothesisType.STATIONARY]})  # so BORN, ainda EMERGING
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=1, timestamp=1.0))  # WEAKENED
    result = build_plans(state)
    assert "engage:track:1" not in result.track_plans


def test_plan_absent_when_conviction_fully_removed():
    state = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY]})
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=3, timestamp=3.0))  # WEAKENED
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=4, timestamp=4.0))  # removido
    result = build_plans(state)
    assert "engage:track:1" not in result.track_plans


def test_entity_plan_created_the_same_way():
    convictions = _convictions_after_n_cycles(3, {}, entity_names=["ball"])
    result = build_plans(convictions)
    plan = result.entity_plans["disengage:entity:ball"]
    assert plan.plan_type == PlanType.DISENGAGE
    assert plan.entity == "ball"


def test_determinism_same_conviction_set_produces_same_planning_set():
    convictions = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY]})
    first = build_plans(convictions).to_dict()
    second = build_plans(convictions).to_dict()
    assert first == second


def test_plan_id_is_stable_across_cycles():
    convictions_3 = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY]})
    convictions_6 = _convictions_after_n_cycles(6, {1: [HypothesisType.STATIONARY]})
    plan_3 = build_plans(convictions_3).track_plans["engage:track:1"]
    plan_6 = build_plans(convictions_6).track_plans["engage:track:1"]
    assert plan_3.plan_id == plan_6.plan_id == "engage:track:1"


def test_to_dict_serialization_with_multiple_plans():
    convictions = _convictions_after_n_cycles(3, {1: [HypothesisType.STATIONARY], 2: [HypothesisType.STATIONARY]})
    result = build_plans(convictions)
    payload = result.to_dict()
    assert list(payload["track_plans"].keys()) == ["engage:track:1", "engage:track:2"]
