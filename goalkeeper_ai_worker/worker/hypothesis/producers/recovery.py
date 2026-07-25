"""produce_recovery_hypothesis: possibilidade de recuperação de
identidade em andamento (Sprint W34) - grounded em
`TrackState.recovery_count >= 1`.

Pode coexistir livremente com stationary/movement/visibility - não é
mutuamente exclusiva com nenhuma delas."""
from __future__ import annotations

from worker.hypothesis.evidence import Evidence
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.perceptual_state.track_state import TrackState

_MIN_RECOVERY_COUNT = 1
_STRONG_RECOVERY_COUNT = 2


def produce_recovery_hypothesis(track_state: TrackState) -> TrackHypothesis | None:
    if track_state.recovery_count < _MIN_RECOVERY_COUNT:
        return None

    conditions = ["recovery_count_at_least_one"]
    evidence = [Evidence("recovery_count", str(track_state.recovery_count))]

    if track_state.recovery_count >= _STRONG_RECOVERY_COUNT:
        conditions.append("recovery_count_at_least_two")

    return TrackHypothesis(
        hypothesis_id=f"recovery:track:{track_state.track_id}",
        hypothesis_type=HypothesisType.RECOVERY,
        track_id=track_state.track_id,
        description=f"Pode haver uma recuperação de identidade associada ao track {track_state.track_id}.",
        evidence=tuple(evidence),
        matching_conditions=tuple(conditions),
        support=len(conditions),
        origin="recovery",
    )
