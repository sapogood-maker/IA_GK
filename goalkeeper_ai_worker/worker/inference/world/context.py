"""WorldModelContext: memória interna MUTÁVEL de uma instância de
`WorldModel` entre chamadas sucessivas a `update()` - NÃO é o
`ProcessorContext` do pipeline (que acumula resultados de TODOS os
Processors); é o análogo, para o World Model, do que
`SceneAnalysisContext` é para `SceneAnalyzer` (Sprint W10).

O estado pertence ao Job - `reset()` é chamado no início de cada Job
(via a mesma plumbing `FrameProcessor.reset()`/`PipelineProcessor.
reset()` já existente desde a W9) para nunca sobreviver entre Jobs."""
from __future__ import annotations

from dataclasses import dataclass, field

from worker.inference.world.object_state import ObjectState


@dataclass
class WorldModelContext:
    """`ObjectState` mais recente conhecido de cada `track_id`."""

    objects: dict[int, ObjectState] = field(default_factory=dict)

    def reset(self) -> None:
        self.objects.clear()
