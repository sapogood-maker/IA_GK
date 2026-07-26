"""ResolutionMethod: como o vencedor de uma decisão foi determinado
(Sprint W39) - taxonomia fechada de 3 valores.

Não é um julgamento de qualidade - só o mecanismo estrutural
observado, derivado de `TrackDecision.winning_criteria` (W37). Nome
deliberadamente evita a palavra "rule" (Rule Engine é explicitamente
excluído do núcleo cognitivo desde W31/W36)."""
from __future__ import annotations

from enum import Enum


class ResolutionMethod(str, Enum):
    SINGLE_CANDIDATE = "single_candidate"
    STRUCTURAL_CRITERION = "structural_criterion"
    DETERMINISTIC_TIEBREAK = "deterministic_tiebreak"
