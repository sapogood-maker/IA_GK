"""Ball: a bola rastreada - nenhuma lógica de chute, gol ou trajetória
esperada vive aqui. Apenas encapsula o próprio estado.

Pode haver zero, uma ou várias instâncias de `Ball` num mesmo
`FootballWorld` (falsos positivos de detecção são possíveis) - escolher
"qual é a bola de verdade" entre candidatas é uma decisão explicitamente
fora de escopo desta sprint (seria uma heurística)."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.types import TrackedFootballEntity


@dataclass
class Ball(TrackedFootballEntity):
    """A bola - ou uma candidata a bola, já que nenhuma heurística de
    desambiguação existe ainda."""
