"""produce_track_visibility_hypothesis / produce_entity_visibility_hypothesis:
possibilidade de que um track/entidade não está mais visível ou está
deixando a cena (Sprint W34).

Duas variantes da mesma HypothesisType.VISIBILITY, diferenciadas pelo
campo `origin` ("visibility_track" vs "visibility_entity") em vez de um
campo novo - grounded em `TrackState.presence_state == ENDED` (track) e
em `EntityState.active_track_ids` vazio + `ended_track_ids` não-vazio
(entity)."""
from __future__ import annotations

from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.perceptual_state.entity_state import EntityState
from worker.perceptual_state.presence_state import PresenceState
from worker.perceptual_state.track_state import TrackState

_MIN_INVISIBLE_DURATION_SECONDS = 1.0


def produce_track_visibility_hypothesis(track_state: TrackState) -> TrackHypothesis | None:
    if track_state.presence_state != PresenceState.ENDED:
        return None

    conditions = ["presence_is_ended"]
    evidence = [Evidence("presence_state", track_state.presence_state.value)]

    time_since = track_state.time_since_last_seen_seconds
    if time_since is not None:
        conditions.append("time_since_last_seen_is_known")
        evidence.append(Evidence("time_since_last_seen_seconds", str(time_since)))
        if time_since >= _MIN_INVISIBLE_DURATION_SECONDS:
            conditions.append("time_since_last_seen_at_least_one_second")

    return TrackHypothesis(
        hypothesis_id=f"visibility:track:{track_state.track_id}",
        hypothesis_type=HypothesisType.VISIBILITY,
        track_id=track_state.track_id,
        description=f"O track {track_state.track_id} aparenta não estar mais visível.",
        evidence=tuple(evidence),
        matching_conditions=tuple(conditions),
        support=len(conditions),
        origin="visibility_track",
    )


def produce_entity_visibility_hypothesis(entity_state: EntityState) -> EntityHypothesis | None:
    if entity_state.active_track_ids or not entity_state.ended_track_ids:
        return None

    conditions = ["no_active_tracks", "has_ended_tracks"]
    evidence = [
        Evidence("active_track_ids", str(len(entity_state.active_track_ids))),
        Evidence("ended_track_ids", str(len(entity_state.ended_track_ids))),
    ]

    return EntityHypothesis(
        hypothesis_id=f"visibility:entity:{entity_state.entity}",
        hypothesis_type=HypothesisType.VISIBILITY,
        entity=entity_state.entity,
        description=f"A entidade '{entity_state.entity}' aparenta estar deixando a cena.",
        evidence=tuple(evidence),
        matching_conditions=tuple(conditions),
        support=len(conditions),
        origin="visibility_entity",
    )
