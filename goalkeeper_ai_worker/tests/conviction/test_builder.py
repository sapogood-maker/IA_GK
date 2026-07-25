"""Testes de worker.conviction.builder.update_convictions - o essencial
da Sprint W35: nascimento, fortalecimento, persistencia, enfraquecimento,
remocao, determinismo, identificadores, conflitos, serializacao."""
from __future__ import annotations

from worker.conviction.builder import update_convictions
from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_set import ConvictionSet
from worker.conviction.conviction_state import ConvictionState
from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis


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


def test_birth_on_first_observation():
    hyp_set = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0)
    result = update_convictions(ConvictionSet(), hyp_set)
    conviction = result.track_convictions["stationary:track:1"]
    assert conviction.state == ConvictionState.BORN
    assert conviction.consecutive_observations == 1
    assert conviction.lifetime_observations == 1
    assert conviction.level == ConvictionLevel.EMERGING


def test_strengthening_crosses_stable_threshold():
    state = ConvictionSet()
    for cycle in range(3):
        hyp_set = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle))
        state = update_convictions(state, hyp_set)
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.consecutive_observations == 3
    assert conviction.level == ConvictionLevel.STABLE
    assert conviction.state == ConvictionState.STRENGTHENED


def test_strengthening_crosses_strong_threshold():
    state = ConvictionSet()
    for cycle in range(6):
        hyp_set = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle))
        state = update_convictions(state, hyp_set)
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.consecutive_observations == 6
    assert conviction.level == ConvictionLevel.STRONG
    assert conviction.state == ConvictionState.STRENGTHENED


def test_persistence_without_crossing_a_level_threshold():
    state = ConvictionSet()
    for cycle in range(2):
        hyp_set = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle))
        state = update_convictions(state, hyp_set)
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.consecutive_observations == 2
    assert conviction.level == ConvictionLevel.EMERGING
    assert conviction.state == ConvictionState.PERSISTED  # cycle 0 = BORN, cycle 1 = PERSISTED (nivel nao mudou)


def test_persistence_duration_measured_from_first_observation():
    state = ConvictionSet()
    for cycle in range(3):
        hyp_set = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle) * 2)
        state = update_convictions(state, hyp_set)
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.first_observed_at_timestamp == 0.0
    assert conviction.persistence_duration_seconds == 4.0  # timestamp do 3o ciclo (4.0) - primeiro (0.0)


def test_weakening_on_first_miss():
    state = update_convictions(ConvictionSet(), _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=1, timestamp=1.0))
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.state == ConvictionState.WEAKENED
    assert conviction.consecutive_observations == 0
    assert conviction.missed_observations == 1
    assert conviction.level == ConvictionLevel.EMERGING
    assert conviction.first_observed_at_frame is None
    assert conviction.persistence_duration_seconds is None


def test_lifetime_observations_preserved_through_weakening():
    state = ConvictionSet()
    for cycle in range(3):
        state = update_convictions(state, _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle)))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=3, timestamp=3.0))
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.lifetime_observations == 3  # preservado, nao reinicia
    assert conviction.consecutive_observations == 0  # streak reiniciado


def test_removal_on_second_consecutive_miss():
    state = update_convictions(ConvictionSet(), _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=1, timestamp=1.0))
    assert "stationary:track:1" in state.track_convictions
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=2, timestamp=2.0))
    assert "stationary:track:1" not in state.track_convictions


def test_reappearance_after_weakening_is_persisted_not_born_again():
    state = update_convictions(ConvictionSet(), _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=1, timestamp=1.0))  # WEAKENED
    state = update_convictions(state, _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=2, timestamp=2.0))
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.state == ConvictionState.PERSISTED
    assert conviction.consecutive_observations == 1
    assert conviction.lifetime_observations == 2  # 1 (born) + 1 (reaparicao) - o ciclo perdido nao conta
    assert conviction.missed_observations == 0


def test_new_birth_after_full_removal_starts_fresh():
    state = update_convictions(ConvictionSet(), _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=1, timestamp=1.0))
    state = update_convictions(state, _hyp_set(track_hyps=[], frame=2, timestamp=2.0))  # removido
    state = update_convictions(state, _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=3, timestamp=3.0))
    conviction = state.track_convictions["stationary:track:1"]
    assert conviction.state == ConvictionState.BORN
    assert conviction.lifetime_observations == 1


def test_determinism_same_inputs_produce_same_output():
    previous = update_convictions(ConvictionSet(), _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=0, timestamp=0.0))
    current = _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=1, timestamp=1.0)
    first = update_convictions(previous, current).to_dict()
    second = update_convictions(previous, current).to_dict()
    assert first == second


def test_identity_two_equal_hypotheses_update_the_same_conviction():
    state = ConvictionSet()
    for cycle in range(2):
        state = update_convictions(state, _hyp_set(track_hyps=[_track_hyp(HypothesisType.STATIONARY, 1)], frame=cycle, timestamp=float(cycle)))
    assert len(state.track_convictions) == 1


def test_conflicting_hypotheses_evolve_independently():
    """MOVEMENT e VISIBILITY do mesmo track nunca interagem - cada uma
    tem sua propria Conviction, evoluindo de forma totalmente
    independente."""
    state = ConvictionSet()
    for cycle in range(3):
        hyp_set = _hyp_set(
            track_hyps=[_track_hyp(HypothesisType.MOVEMENT, 1), _track_hyp(HypothesisType.VISIBILITY, 1)],
            frame=cycle,
            timestamp=float(cycle),
        )
        state = update_convictions(state, hyp_set)
    movement = state.track_convictions["movement:track:1"]
    visibility = state.track_convictions["visibility:track:1"]
    assert movement.consecutive_observations == 3
    assert visibility.consecutive_observations == 3
    assert movement.level == visibility.level == ConvictionLevel.STABLE


def test_entity_convictions_evolve_the_same_way():
    state = ConvictionSet()
    for cycle in range(3):
        state = update_convictions(state, _hyp_set(entity_hyps=[_entity_hyp("ball")], frame=cycle, timestamp=float(cycle)))
    conviction = state.entity_convictions["visibility:entity:ball"]
    assert conviction.consecutive_observations == 3
    assert conviction.level == ConvictionLevel.STABLE


def test_empty_hypothesis_set_and_empty_previous_produces_empty_conviction_set():
    result = update_convictions(ConvictionSet(), HypothesisSet())
    assert result.track_convictions == {}
    assert result.entity_convictions == {}


def test_to_dict_serialization_with_multiple_convictions():
    state = ConvictionSet()
    hyp_set = _hyp_set(
        track_hyps=[_track_hyp(HypothesisType.STATIONARY, 3), _track_hyp(HypothesisType.STATIONARY, 1)],
        frame=0,
        timestamp=0.0,
    )
    state = update_convictions(state, hyp_set)
    payload = state.to_dict()
    assert list(payload["track_convictions"].keys()) == ["stationary:track:1", "stationary:track:3"]
