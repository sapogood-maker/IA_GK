"""update_convictions: projeta o próximo ConvictionSet a partir do
ConvictionSet anterior + o HypothesisSet atual (Sprint W35).

Função pura - recebe o estado anterior EXPLICITAMENTE como argumento
(nunca um objeto stateful escondido), compara contra as hipóteses
atuais, e devolve o próximo ConvictionSet. O(número de convicções
anteriores + número de hipóteses atuais) - nunca volta a WorkingState,
TemporalMemory, Timeline ou Event; só lê `current.track_hypotheses`/
`entity_hypotheses` e `current.observed_at_frame`/`observed_at_timestamp`
(o "relógio" já emprestado de WorkingState via HypothesisSet, W34)."""
from __future__ import annotations

from worker.conviction.conviction_level import level_for
from worker.conviction.conviction_set import ConvictionSet
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.entity_conviction import EntityConviction
from worker.conviction.track_conviction import TrackConviction
from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.track_hypothesis import TrackHypothesis

_MAX_CONSECUTIVE_MISSES = 1


def update_convictions(previous: ConvictionSet, current: HypothesisSet) -> ConvictionSet:
    now_frame = current.observed_at_frame
    now_timestamp = current.observed_at_timestamp

    track_convictions = _update_track_convictions(
        previous.track_convictions, current.track_hypotheses, now_frame, now_timestamp
    )
    entity_convictions = _update_entity_convictions(
        previous.entity_convictions, current.entity_hypotheses, now_frame, now_timestamp
    )

    return ConvictionSet(
        track_convictions=track_convictions,
        entity_convictions=entity_convictions,
        observed_at_frame=now_frame,
        observed_at_timestamp=now_timestamp,
    )


def _update_track_convictions(
    previous_map: dict[str, TrackConviction],
    current_hyps: tuple[TrackHypothesis, ...],
    now_frame: int | None,
    now_timestamp: float | None,
) -> dict[str, TrackConviction]:
    current_by_id = {h.hypothesis_id: h for h in current_hyps}
    result: dict[str, TrackConviction] = {}
    for hid in sorted(set(previous_map) | set(current_by_id)):
        prev = previous_map.get(hid)
        hyp = current_by_id.get(hid)
        if hyp is not None:
            result[hid] = _observed_track_conviction(prev, hyp, now_frame, now_timestamp)
        else:
            conviction = _missed_track_conviction(prev)
            if conviction is not None:
                result[hid] = conviction
    return result


def _observed_track_conviction(
    prev: TrackConviction | None, hyp: TrackHypothesis, now_frame: int | None, now_timestamp: float | None
) -> TrackConviction:
    if prev is None:
        consecutive = 1
        lifetime = 1
        first_frame = now_frame
        first_timestamp = now_timestamp
        state = ConvictionState.BORN
    else:
        streak_broken = prev.consecutive_observations == 0
        consecutive = 1 if streak_broken else prev.consecutive_observations + 1
        lifetime = prev.lifetime_observations + 1
        first_frame = now_frame if streak_broken else prev.first_observed_at_frame
        first_timestamp = now_timestamp if streak_broken else prev.first_observed_at_timestamp
        new_level = level_for(consecutive)
        state = ConvictionState.STRENGTHENED if new_level != prev.level else ConvictionState.PERSISTED

    duration = (
        now_timestamp - first_timestamp if now_timestamp is not None and first_timestamp is not None else None
    )
    return TrackConviction(
        hypothesis_id=hyp.hypothesis_id,
        hypothesis_type=hyp.hypothesis_type,
        track_id=hyp.track_id,
        consecutive_observations=consecutive,
        lifetime_observations=lifetime,
        missed_observations=0,
        first_observed_at_frame=first_frame,
        first_observed_at_timestamp=first_timestamp,
        persistence_duration_seconds=duration,
        state=state,
        level=level_for(consecutive),
    )


def _missed_track_conviction(prev: TrackConviction | None) -> TrackConviction | None:
    missed = prev.missed_observations + 1
    if missed > _MAX_CONSECUTIVE_MISSES:
        return None

    return TrackConviction(
        hypothesis_id=prev.hypothesis_id,
        hypothesis_type=prev.hypothesis_type,
        track_id=prev.track_id,
        consecutive_observations=0,
        lifetime_observations=prev.lifetime_observations,
        missed_observations=missed,
        first_observed_at_frame=None,
        first_observed_at_timestamp=None,
        persistence_duration_seconds=None,
        state=ConvictionState.WEAKENED,
        level=level_for(0),
    )


def _update_entity_convictions(
    previous_map: dict[str, EntityConviction],
    current_hyps: tuple[EntityHypothesis, ...],
    now_frame: int | None,
    now_timestamp: float | None,
) -> dict[str, EntityConviction]:
    current_by_id = {h.hypothesis_id: h for h in current_hyps}
    result: dict[str, EntityConviction] = {}
    for hid in sorted(set(previous_map) | set(current_by_id)):
        prev = previous_map.get(hid)
        hyp = current_by_id.get(hid)
        if hyp is not None:
            result[hid] = _observed_entity_conviction(prev, hyp, now_frame, now_timestamp)
        else:
            conviction = _missed_entity_conviction(prev)
            if conviction is not None:
                result[hid] = conviction
    return result


def _observed_entity_conviction(
    prev: EntityConviction | None, hyp: EntityHypothesis, now_frame: int | None, now_timestamp: float | None
) -> EntityConviction:
    if prev is None:
        consecutive = 1
        lifetime = 1
        first_frame = now_frame
        first_timestamp = now_timestamp
        state = ConvictionState.BORN
    else:
        streak_broken = prev.consecutive_observations == 0
        consecutive = 1 if streak_broken else prev.consecutive_observations + 1
        lifetime = prev.lifetime_observations + 1
        first_frame = now_frame if streak_broken else prev.first_observed_at_frame
        first_timestamp = now_timestamp if streak_broken else prev.first_observed_at_timestamp
        new_level = level_for(consecutive)
        state = ConvictionState.STRENGTHENED if new_level != prev.level else ConvictionState.PERSISTED

    duration = (
        now_timestamp - first_timestamp if now_timestamp is not None and first_timestamp is not None else None
    )
    return EntityConviction(
        hypothesis_id=hyp.hypothesis_id,
        hypothesis_type=hyp.hypothesis_type,
        entity=hyp.entity,
        consecutive_observations=consecutive,
        lifetime_observations=lifetime,
        missed_observations=0,
        first_observed_at_frame=first_frame,
        first_observed_at_timestamp=first_timestamp,
        persistence_duration_seconds=duration,
        state=state,
        level=level_for(consecutive),
    )


def _missed_entity_conviction(prev: EntityConviction | None) -> EntityConviction | None:
    missed = prev.missed_observations + 1
    if missed > _MAX_CONSECUTIVE_MISSES:
        return None

    return EntityConviction(
        hypothesis_id=prev.hypothesis_id,
        hypothesis_type=prev.hypothesis_type,
        entity=prev.entity,
        consecutive_observations=0,
        lifetime_observations=prev.lifetime_observations,
        missed_observations=missed,
        first_observed_at_frame=None,
        first_observed_at_timestamp=None,
        persistence_duration_seconds=None,
        state=ConvictionState.WEAKENED,
        level=level_for(0),
    )
