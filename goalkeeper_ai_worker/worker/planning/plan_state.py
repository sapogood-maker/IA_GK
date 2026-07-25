"""PlanState: o que aconteceu com um plano NESTE ciclo (Sprint W36).

'Ser abandonado' não é um valor aqui - um plano abandonado simplesmente
não aparece no PlanningSet seguinte (mesma disciplina de
ConvictionState/W35: ausência representa ausência, nunca um valor
fabricado)."""
from __future__ import annotations

from enum import Enum


class PlanState(str, Enum):
    EMERGED = "emerged"
    ONGOING = "ongoing"
    INVALIDATED = "invalidated"
