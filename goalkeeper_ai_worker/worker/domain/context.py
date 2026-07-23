"""FootballDomainContext: memória interna do FootballWorldBuilder entre
chamadas sucessivas a `build()` - NÃO é o `ProcessorContext` do pipeline.

Guarda `Field`/`Goal` (entidades ESTÁTICAS, que representam o campo/
balizas do vídeo inteiro) para que sejam construídas UMA vez e
reaproveitadas em cada frame, em vez de recriadas do zero a cada chamada
- sem isso, cada `FootballWorld` teria uma instância de `Field`
tecnicamente diferente (mesmo com os mesmos valores), o que não faz
sentido para uma entidade que representa o mesmo campo físico do início
ao fim do vídeo.

O estado pertence ao Job - `reset()` é chamado no início de cada Job (via
a mesma plumbing `FrameProcessor.reset()`/`PipelineProcessor.reset()` já
existente desde a W9) para nunca sobreviver entre Jobs - aplicando a
lição da W9 PROATIVAMENTE, sem precisar redescobri-la."""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from worker.domain.entities.field import Field
from worker.domain.entities.goal import Goal


@dataclass
class FootballDomainContext:
    """Campo/balizas já construídos nesta execução - `None`/vazio até a
    primeira chamada a `build()`."""

    field: Field | None = None
    goals: list[Goal] = dataclass_field(default_factory=list)

    def reset(self) -> None:
        self.field = None
        self.goals = []
