"""run_cognitive_core: executa a cadeia inteira do Cognitive Core sobre
um `event_timeline` real, produzindo uma decisão por `PlaySegment`
(Phase 2, G2A).

Ordem exata (plano aprovado): TimelineExplorer -> PlaySegmenter ->
EnrichmentPipeline -> build_temporal_memory -> build_working_state ->
build_hypotheses -> update_convictions -> build_plans -> decide ->
evaluate. `ConvictionSet` é encadeado ENTRE segmentos (cada jogada real
= um ciclo de observação) - nunca reinicializado a cada segmento.

Reutiliza exclusivamente funções/classes já existentes das 11 camadas
congeladas - nenhuma delas é modificada, nenhuma lógica é duplicada."""
from __future__ import annotations

from worker.conviction.builder import update_convictions
from worker.conviction.conviction_set import ConvictionSet
from worker.decision.builder import decide
from worker.evaluation.builder import evaluate
from worker.explorers.timeline_explorer import TimelineExplorer
from worker.hypothesis.builder import build_hypotheses
from worker.memory.builder import build_temporal_memory
from worker.perceptual_state.builder import build_working_state
from worker.planning.builder import build_plans
from worker.segments.factory import create_strategy
from worker.segments.segmenter import PlaySegmenter
from worker.timeline.enrichment.enrichers.motion_transitions import MotionTransitionEnricher
from worker.timeline.enrichment.enrichers.track_recovery import TrackRecoveryConfidenceEnricher
from worker.timeline.enrichment.enrichers.track_stability import TrackStabilityEnricher
from worker.timeline.enrichment.pipeline import EnrichmentPipeline

_ENRICHERS = [
    MotionTransitionEnricher(),
    MotionTransitionEnricher(entity_filter="ball"),
    TrackStabilityEnricher(),
    TrackRecoveryConfidenceEnricher(),
]


def run_cognitive_core(event_timeline: list[dict]) -> list[dict]:
    """Recebe o mesmo `event_timeline` já produzido por `build_timeline`
    (W28, via `state.event_timeline` ou `artifact["event_timeline"]`) e
    devolve uma lista de resultados, um por `PlaySegment`, em ordem
    cronológica: `{"segment_id", "start_frame", "end_frame",
    "decision_set", "evaluation_set"}` (dicts simples, via `.to_dict()`
    de cada camada - nunca uma dataclass nova)."""
    explorer = TimelineExplorer({"event_timeline": event_timeline})
    raw = explorer.chronological()

    derived = [event.to_dict() for event in EnrichmentPipeline(_ENRICHERS).run(raw)]
    combined = sorted(raw + derived, key=lambda event: event["frame_index"])

    strategy = create_strategy("gap")
    segments = PlaySegmenter(strategy).segment(explorer)

    conviction_set = ConvictionSet()
    results: list[dict] = []
    for segment in segments:
        segment_events = [
            event for event in combined if segment.start_frame <= event["frame_index"] <= segment.end_frame
        ]

        memory = build_temporal_memory(segment_events)
        working_state = build_working_state(memory)
        hypotheses = build_hypotheses(working_state)
        conviction_set = update_convictions(conviction_set, hypotheses)
        planning_set = build_plans(conviction_set)
        decision_set = decide(planning_set)
        evaluation_set = evaluate(decision_set)

        results.append(
            {
                "segment_id": segment.segment_id,
                "start_frame": segment.start_frame,
                "end_frame": segment.end_frame,
                "decision_set": decision_set.to_dict(),
                "evaluation_set": evaluation_set.to_dict(),
            }
        )

    return results
