"""Goalkeeper: um goleiro rastreado - nenhuma lógica de defesa, saída,
reposição ou mergulho vive aqui (isso é responsabilidade de sprints
futuras, Seção 16 da Constituição). Apenas encapsula o próprio estado."""
from __future__ import annotations

from dataclasses import dataclass

from worker.domain.types import TrackedFootballEntity


@dataclass
class Goalkeeper(TrackedFootballEntity):
    """Um goleiro - estruturalmente idêntico a `Player` nesta sprint
    (nenhum sinal no pipeline hoje distingue goleiro de jogador além de
    um rótulo de classe dedicado, que o modelo padrão - YOLO11n, treinado
    em COCO - não produz). Classe própria de propósito, para que
    `GoalkeeperAnalyzer` (Sprint W13+) possa exigir este tipo
    especificamente, não uma união genérica."""
