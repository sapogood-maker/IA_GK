"""PlanType: taxonomia fechada de planos possíveis (Sprint W36).

4 valores, vocabulário genérico de rastreamento/percepção - nunca uma
tática específica de domínio (futebol/goleiro). Mapeamento 1:1 com
`HypothesisType` (W34) é uma escolha de implementação desta sprint, não
um contrato permanente - ver `worker/planning/builder.py` para a função
de mapeamento (documento arquitetural da W36, Seção 6)."""
from __future__ import annotations

from enum import Enum


class PlanType(str, Enum):
    ENGAGE = "engage"
    PURSUE = "pursue"
    REACQUIRE = "reacquire"
    DISENGAGE = "disengage"
