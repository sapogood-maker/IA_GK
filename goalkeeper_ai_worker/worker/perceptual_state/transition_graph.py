"""TransitionGraph: abstração de domínio para "quais transições são
legítimas" de UMA dimensão de estado (Sprint W33).

Substitui tabelas globais de transições soltas - encapsula o grafo E a
operação sobre ele (`is_legal`), reutilizável por qualquer dimensão de
estado (motion, presence, futuras) sem duplicar a forma de consulta.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionGraph:
    """Conjunto imutável de pares (from_state, to_state) considerados
    legítimos - representados como strings (não o Enum concreto), para
    que a mesma classe sirva qualquer dimensão sem acoplamento a um
    Enum específico."""

    legal_transitions: frozenset[tuple[str, str]]

    def is_legal(self, from_state: str, to_state: str) -> bool:
        return (from_state, to_state) in self.legal_transitions
