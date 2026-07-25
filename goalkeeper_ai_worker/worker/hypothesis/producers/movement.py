"""produce_movement_hypothesis: possibilidade de que o objeto está em
movimento (Sprint W34) - grounded em `TrackState.motion_state == MOVING`.

Espelho exato de `stationary.py` - mutuamente exclusiva com ela por
construção, já que `motion_state` é um único valor por vez."""
from __future__ import annotations

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.track_state import TrackState

_MIN_STABLE_DURATION_SECONDS = 1.0


def produce_movement_hypothesis(track_state: TrackState) -> TrackHypothesis | None:
    if track_state.motion_state != MotionState.MOVING:
        return None

    conditions = ["motion_state_is_moving"]
    evidence = [Evidence("motion_state", track_state.motion_state.value)]

    duration = track_state.motion_state_duration_seconds
    if duration is not None:
        conditions.append("duration_is_known")
        evidence.append(Evidence("motion_state_duration_seconds", str(duration)))
        if duration >= _MIN_STABLE_DURATION_SECONDS:
            conditions.append("duration_at_least_one_second")

    return TrackHypothesis(
        hypothesis_id=f"movement:track:{track_state.track_id}",
        hypothesis_type=HypothesisType.MOVEMENT,
        track_id=track_state.track_id,
        description=f"O objeto no track {track_state.track_id} aparenta estar em movimento.",
        evidence=tuple(evidence),
        matching_conditions=tuple(conditions),
        support=len(conditions),
        origin="movement",
    )
