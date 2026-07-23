"""Direction: direção de jogo (qual lado o time ataca) - conceito
categórico do domínio, distinto do ângulo contínuo de `Vector` (que
descreve o movimento instantâneo de um objeto, não a direção de ataque
combinada de uma partida/período).

Sem calibração de câmera ou marcações do campo disponíveis nesta camada
(Seção 6.1 da Constituição), o valor default é sempre `UNKNOWN` - nenhuma
heurística tenta inferir isso nesta sprint."""
from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    UNKNOWN = "unknown"
