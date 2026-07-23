"""Player: um jogador de linha rastreado - nenhuma lógica de time,
posição tática ou papel vive aqui. Apenas encapsula o próprio estado."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.types import TrackedFootballEntity


@dataclass
class Player(TrackedFootballEntity):
    """Um jogador - qualquer pessoa detectada que não seja identificada
    como goleiro (Seção 6.1 da Constituição: hoje, com o rótulo `"person"`
    do modelo padrão, isso é TODO mundo)."""
