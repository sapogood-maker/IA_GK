"""build_hypotheses: projeta um HypothesisSet a partir de um WorkingState
já construído (Sprint W34).

Função pura - recalcula o HypothesisSet inteiro a cada chamada, do zero.
O(número de tracks + número de entidades) de `working_state` - cada
track/entidade passa por um número FIXO de produtores, nunca volta a
`TemporalMemory`, `Timeline` ou `Event`. `sorted()` explícito garante
determinismo independente da ordem interna de `dict`."""
from __future__ import annotations

from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.producers.movement import produce_movement_hypothesis
from worker.hypothesis.producers.recovery import produce_recovery_hypothesis
from worker.hypothesis.producers.stationary import produce_stationary_hypothesis
from worker.hypothesis.producers.visibility import (
    produce_entity_visibility_hypothesis,
    produce_track_visibility_hypothesis,
)
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.track_state import TrackState
from worker.perceptual_state.working_state import WorkingState

_TRACK_PRODUCERS = (
    produce_stationary_hypothesis,
    produce_movement_hypothesis,
    produce_recovery_hypothesis,
    produce_track_visibility_hypothesis,
)

_ENTITY_PRODUCERS = (produce_entity_visibility_hypothesis,)


def build_hypotheses(working_state: WorkingState) -> HypothesisSet:
    track_hypotheses = tuple(
        hyp
        for track_id in sorted(working_state.track_states)
        for hyp in _track_hypotheses_for(working_state.track_states[track_id])
    )
    entity_hypotheses = tuple(
        hyp
        for entity in sorted(working_state.entity_states)
        for hyp in _entity_hypotheses_for(working_state.entity_states[entity])
    )

    return HypothesisSet(
        track_hypotheses=track_hypotheses,
        entity_hypotheses=entity_hypotheses,
        observed_at_frame=working_state.observed_at_frame,
        observed_at_timestamp=working_state.observed_at_timestamp,
        source_track_count=working_state.source_track_count,
    )


def _track_hypotheses_for(track_state: TrackState) -> tuple[TrackHypothesis, ...]:
    return tuple(hyp for producer in _TRACK_PRODUCERS if (hyp := producer(track_state)) is not None)


def _entity_hypotheses_for(entity_state: EntityState) -> tuple[EntityHypothesis, ...]:
    return tuple(hyp for producer in _ENTITY_PRODUCERS if (hyp := producer(entity_state)) is not None)
