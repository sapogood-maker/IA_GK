"""HypothesisSet: raiz do conjunto de hipóteses (Sprint W34) - um por
chamada de `build_hypotheses`.

Diferente de `WorkingState.track_states` (exatamente 1 `TrackState` por
track), um track pode gerar 0 a N hipóteses simultâneas - por isso
`track_hypotheses`/`entity_hypotheses` são tuplas, não dicts chaveados
por id."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.hypothesis.entity_hypothesis import EntityHypothesis
from worker.hypothesis.track_hypothesis import TrackHypothesis


@dataclass(frozen=True)
class HypothesisSet:
    track_hypotheses: tuple[TrackHypothesis, ...] = field(default_factory=tuple)
    entity_hypotheses: tuple[EntityHypothesis, ...] = field(default_factory=tuple)
    observed_at_frame: int | None = None
    observed_at_timestamp: float | None = None
    source_track_count: int = 0

    def to_dict(self) -> dict:
        return {
            "track_hypotheses": [
                h.to_dict() for h in sorted(self.track_hypotheses, key=lambda h: h.hypothesis_id)
            ],
            "entity_hypotheses": [
                h.to_dict() for h in sorted(self.entity_hypotheses, key=lambda h: h.hypothesis_id)
            ],
            "observed_at_frame": self.observed_at_frame,
            "observed_at_timestamp": self.observed_at_timestamp,
            "source_track_count": self.source_track_count,
        }
