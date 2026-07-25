"""ConvictionLevel: nível discreto de crença (Sprint W35) - NUNCA
porcentagem/probabilidade/ML score.

`level_for()` é a única fonte de verdade que deriva o nível a partir de
`consecutive_observations` - o campo `level` de uma Conviction nunca é
setado diretamente, sempre por esta função pura."""
from __future__ import annotations

from enum import Enum


class ConvictionLevel(str, Enum):
    EMERGING = "emerging"
    STABLE = "stable"
    STRONG = "strong"


_STABLE_THRESHOLD = 3
_STRONG_THRESHOLD = 6


def level_for(consecutive_observations: int) -> ConvictionLevel:
    if consecutive_observations >= _STRONG_THRESHOLD:
        return ConvictionLevel.STRONG
    if consecutive_observations >= _STABLE_THRESHOLD:
        return ConvictionLevel.STABLE
    return ConvictionLevel.EMERGING
