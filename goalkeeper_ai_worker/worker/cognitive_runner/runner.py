"""run_cognitive_core: executa a cadeia inteira do Cognitive Core sobre
um `event_timeline` real, produzindo uma decisão por `PlaySegment`
(Phase 2, G2A).

Ordem exata (plano aprovado): TimelineExplorer -> PlaySegmenter ->
EnrichmentPipeline -> build_temporal_memory -> build_working_state ->
build_hypotheses -> update_convictions -> build_plans -> decide ->
evaluate. `ConvictionSet` é encadeado ENTRE segmentos (cada jogada real
= um ciclo de observação) - nunca reinicializado a cada segmento.

Reutiliza exclusivamente funções/classes já existentes das 11 camadas
congeladas - nenhuma delas é modificada, nenhuma lógica é duplicada.

G2D: a cadeia roda uma unica vez por chamada, dentro de `_execute()`, que
retem os objetos intermediarios (HypothesisSet/ConvictionSet/PlanningSet/
etc. - todos ja existentes, nenhuma dataclass nova) e o tempo gasto em
cada camada num "Execution Trace" (dict/list simples). `run_cognitive_core`
mantem o MESMO contrato publico de sempre (mesma assinatura, mesmo
retorno) - agora so um wrapper fino sobre `_execute()`.
`run_cognitive_core_with_trace` expoe tambem o trace, para quem precisar
de observabilidade (worker/cognitive_runner/report.py) sem rodar a cadeia
de novo."""
from __future__ import annotations

from time import perf_counter

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


def _ms(seconds: float) -> float:
    return seconds * 1000.0


def _execute(event_timeline: list[dict]) -> dict:
    """Roda a cadeia real UMA VEZ, retendo os objetos intermediarios de
    cada segmento e o tempo gasto em cada camada - o "Execution Trace".
    Formato: dict/list simples cujas folhas sao as MESMAS instancias de
    dataclass que o Core ja produzia internamente (nenhuma dataclass nova
    e criada aqui)."""
    execute_t0 = perf_counter()

    t0 = perf_counter()
    explorer = TimelineExplorer({"event_timeline": event_timeline})
    raw = explorer.chronological()
    timeline_ms = _ms(perf_counter() - t0)

    t0 = perf_counter()
    strategy = create_strategy("gap")
    segments = PlaySegmenter(strategy).segment(explorer)
    segmentation_ms = _ms(perf_counter() - t0)

    t0 = perf_counter()
    derived = [event.to_dict() for event in EnrichmentPipeline(_ENRICHERS).run(raw)]
    combined = sorted(raw + derived, key=lambda event: event["frame_index"])
    enrichment_ms = _ms(perf_counter() - t0)

    conviction_set = ConvictionSet()
    segment_entries: list[dict] = []
    for segment in segments:
        segment_events = [
            event for event in combined if segment.start_frame <= event["frame_index"] <= segment.end_frame
        ]

        t0 = perf_counter()
        memory = build_temporal_memory(segment_events)
        memory_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        working_state = build_working_state(memory)
        working_state_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        hypotheses = build_hypotheses(working_state)
        hypothesis_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        conviction_set = update_convictions(conviction_set, hypotheses)
        conviction_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        planning_set = build_plans(conviction_set)
        planning_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        decision_set = decide(planning_set)
        decision_ms = _ms(perf_counter() - t0)

        t0 = perf_counter()
        evaluation_set = evaluate(decision_set)
        evaluation_ms = _ms(perf_counter() - t0)

        segment_entries.append(
            {
                "segment": segment,
                "segment_events": segment_events,
                "memory": memory,
                "working_state": working_state,
                "hypotheses": hypotheses,
                "conviction_set": conviction_set,
                "planning_set": planning_set,
                "decision_set": decision_set,
                "evaluation_set": evaluation_set,
                "timing_ms": {
                    "memory": memory_ms,
                    "working_state": working_state_ms,
                    "hypothesis": hypothesis_ms,
                    "conviction": conviction_ms,
                    "planning": planning_ms,
                    "decision": decision_ms,
                    "evaluation": evaluation_ms,
                },
            }
        )

    return {
        "raw_events": raw,
        "derived_events": derived,
        "segments": segment_entries,
        "timing_ms": {
            "timeline": timeline_ms,
            "segmentation": segmentation_ms,
            "enrichment": enrichment_ms,
            "execute_total": _ms(perf_counter() - execute_t0),
        },
    }


def _segment_result(entry: dict) -> dict:
    segment = entry["segment"]
    return {
        "segment_id": segment.segment_id,
        "start_frame": segment.start_frame,
        "end_frame": segment.end_frame,
        "decision_set": entry["decision_set"].to_dict(),
        "evaluation_set": entry["evaluation_set"].to_dict(),
    }


def run_cognitive_core(event_timeline: list[dict]) -> list[dict]:
    """Recebe o mesmo `event_timeline` já produzido por `build_timeline`
    (W28, via `state.event_timeline` ou `artifact["event_timeline"]`) e
    devolve uma lista de resultados, um por `PlaySegment`, em ordem
    cronológica: `{"segment_id", "start_frame", "end_frame",
    "decision_set", "evaluation_set"}` (dicts simples, via `.to_dict()`
    de cada camada - nunca uma dataclass nova).

    Contrato inalterado desde a G2A (mesma assinatura, mesmo retorno) -
    por dentro, desde a G2D, e so um wrapper fino sobre `_execute()`."""
    trace = _execute(event_timeline)
    return [_segment_result(entry) for entry in trace["segments"]]


def run_cognitive_core_with_trace(event_timeline: list[dict]) -> tuple[list[dict], dict]:
    """Mesmos `results` de `run_cognitive_core`, mais o Execution Trace
    completo (G2D) - para quem precisar dos estados intermediarios/tempos
    por camada (worker/cognitive_runner/report.py) sem rodar a cadeia de
    novo. O Core roda exatamente uma vez por chamada."""
    trace = _execute(event_timeline)
    results = [_segment_result(entry) for entry in trace["segments"]]
    return results, trace
