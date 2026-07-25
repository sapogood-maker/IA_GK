"""EnrichmentPipeline: roda uma lista de Enrichers habilitados sobre a
MESMA entrada original (Sprint W31).

Principio obrigatorio (documento arquitetural e confirmacao do usuario
antes desta implementacao): todos os Enrichers sao independentes entre
si e trabalham sobre a MESMA lista de eventos de entrada - nenhum
Enricher nesta sprint consome a saida derivada de outro (nunca encadeia).
Isso e o motivo de `run()` chamar `enricher.enrich(events)` para cada
Enricher usando sempre o `events` original recebido, nunca o resultado
acumulado.

Deliberadamente NAO reaproveita `PipelineProcessor` (worker/inference/
processors/pipeline.py) como classe-base ou dependencia direta - copiar
o PADRAO (orquestrar uma lista de plugins habilitados) e desejavel;
importar a CLASSE misturaria um conceito de frame-a-frame (Processor)
com um conceito de scan-de-eventos (Enricher), que operam em
granularidades diferentes."""
from __future__ import annotations

from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.event import Event


class EnrichmentPipeline:
    def __init__(self, enrichers: list[Enricher]) -> None:
        self._enrichers = enrichers

    def run(self, events: list[dict]) -> list[Event]:
        """Cada Enricher habilitado recebe o MESMO `events` de entrada.
        A saida final e concatenada e reordenada por frame_index (sorted
        estavel) - determinismo garantido: mesma entrada, mesma ordem de
        saida, sempre."""
        derived: list[Event] = []
        for enricher in self._enrichers:
            derived.extend(enricher.enrich(events))
        return sorted(derived, key=lambda event: event.frame_index)
