"""ConvictionState: o que aconteceu com uma Conviction NESTE ciclo -
transição, nunca força (Sprint W35).

'Desaparecer' não é um valor aqui: uma Conviction removida simplesmente
não aparece no ConvictionSet seguinte - ausência representa ausência,
nunca um valor fabricado (mesma disciplina de W33/W34)."""
from __future__ import annotations

from enum import Enum


class ConvictionState(str, Enum):
    BORN = "born"
    STRENGTHENED = "strengthened"
    PERSISTED = "persisted"
    WEAKENED = "weakened"
