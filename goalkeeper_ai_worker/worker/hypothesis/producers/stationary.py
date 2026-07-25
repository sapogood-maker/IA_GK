"""produce_stationary_hypothesis: possibilidade de que o objeto está
parado (Sprint W34) - grounded em `TrackState.motion_state == STOPPED`."""
from __future__ import annotations

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.perceptual_state.motion_state import MotionState
from worker.perceptual_state.track_state import TrackState

_MIN_STABLE_DURATION_SECONDS = 1.0


def produce_stationary_hypothesis(track_state: TrackState) -> TrackHypothesis | None:
    if track_state.motion_state != MotionState.STOPPED:
        return None

    conditions = ["motion_state_is_stopped"]
    evidence = [Evidence("motion_state", track_state.motion_state.value)]

    duration = track_state.motion_state_duration_seconds
    if duration is not None:
        conditions.append("duration_is_known")
        evidence.append(Evidence("motion_state_duration_seconds", str(duration)))
        if duration >= _MIN_STABLE_DURATION_SECONDS:
            conditions.append("duration_at_least_one_second")

    return TrackHypothesis(
        hypothesis_id=f"stationary:track:{track_state.track_id}",
        hypothesis_type=HypothesisType.STATIONARY,
        track_id=track_state.track_id,
        description=f"O objeto no track {track_state.track_id} aparenta estar parado.",
        evidence=tuple(evidence),
        matching_conditions=tuple(conditions),
        support=len(conditions),
        origin="stationary",
    )
