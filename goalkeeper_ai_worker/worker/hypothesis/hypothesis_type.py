"""HypothesisType: taxonomia fechada de possibilidades (Sprint W34).

4 valores - cada um só existe porque há um campo real em
`TrackState`/`EntityState` (W33) que o sustenta sem inventar dado.
`TrajectoryHypothesis` (sugerida no pedido original) foi deliberadamente
descartada: WorkingState não carrega posição/direção (ver documento
arquitetural da W34, Seção 3)."""
from __future__ import annotations

from enum import Enum


class HypothesisType(str, Enum):
    STATIONARY = "stationary"
    MOVEMENT = "movement"
    RECOVERY = "recovery"
    VISIBILITY = "visibility"
