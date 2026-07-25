"""TrackRecoveryConfidenceEnricher: deriva TrackRecoveredWithConfidence
correlacionando TrackRecovered (sem confianca) com ObjectDetected (com
confianca) do MESMO frame_index e MESMO rotulo normalizado (Sprint W31).

Correlacao dentro de um UNICO frame - o caso mais simples e menos
ambiguo de "Correlacao de Entidade" (documento arquitetural W31, Secao
3): so precisa achar UM candidato no mesmo frame, nunca rastrear ao
longo de varios frames (isso e Nivel 2, fora de escopo). Se houver mais
de um candidato (2+ deteccoes do mesmo rotulo no mesmo frame), escolhe
deterministicamente o PRIMEIRO na ordem de `events` (nunca inventa
desempate por posicao/confianca - mesma filosofia de "nao decidir sem
dado" ja usada em GoalGeometryAnalyzer). Sem correspondencia, nao emite
nada - nunca inventa confianca.

Primeiro exemplo real de `Provenance` com MAIS de um evento de origem
(o proprio `TrackRecovered` + o `ObjectDetected` correlacionado) - prova
de que o mecanismo (Secao 5-A do documento) funciona sem exigir mudanca
de schema em `Event`.
"""
from __future__ import annotations

from worker.timeline import event_types as timeline_event_types
from worker.timeline.enrichment import event_types as enrichment_event_types
from worker.timeline.enrichment.entity_normalization import normalize_entity_label
from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.enrichment.provenance import Provenance
from worker.timeline.event import Event


class TrackRecoveryConfidenceEnricher(Enricher):
    name = "track_recovery"

    def enrich(self, events: list[dict]) -> list[Event]:
        # Passada 1 (O(n)): indexa ObjectDetected por (frame_index, rotulo
        # normalizado) - permite lookup O(1) na passada 2, em vez de
        # rebuscar `events` a cada TrackRecovered (evita O(n^2)).
        detections_by_frame_entity: dict[tuple[int, str | None], list[dict]] = {}
        for event in events:
            if event["event_type"] == timeline_event_types.OBJECT_DETECTED:
                key = (event["frame_index"], normalize_entity_label(event["entity"]))
                detections_by_frame_entity.setdefault(key, []).append(event)

        # Passada 2 (O(n)): resolve cada TrackRecovered via o indice acima.
        derived: list[Event] = []
        for event in events:
            if event["event_type"] != timeline_event_types.TRACK_RECOVERED:
                continue

            normalized_entity = normalize_entity_label(event["entity"])
            candidates = detections_by_frame_entity.get((event["frame_index"], normalized_entity))
            if not candidates:
                continue
            matched_detection = candidates[0]

            provenance = Provenance(source_event_ids=(event["event_id"], matched_detection["event_id"]))
            derived.append(
                Event(
                    event_type=enrichment_event_types.TRACK_RECOVERED_WITH_CONFIDENCE,
                    frame_index=event["frame_index"],
                    timestamp_seconds=event["timestamp_seconds"],
                    track_id=event["track_id"],
                    entity=normalized_entity,
                    position=matched_detection["position"],
                    confidence=matched_detection["confidence"],
                    metadata={"provenance": list(provenance.source_event_ids)},
                    parent_event_id=provenance.primary_parent_id,
                )
            )

        return derived
