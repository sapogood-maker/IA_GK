"""build_cognitive_report: observabilidade/explicabilidade sobre uma
execucao do Cognitive Core (Phase 2, G2C/G2D) - metricas, contagens,
tempos e, para cada PlaySegment, a primeira etapa que interrompeu o fluxo
quando nenhuma decisao foi produzida.

Esta sprint e EXCLUSIVAMENTE observacional: nao produz nenhuma decisao nova,
nao adiciona heuristica alguma, e nao altera o comportamento de nenhuma
camada do Cognitive Core (congeladas desde o Architecture Freeze v1.0) nem
de `worker/cognitive_runner/runner.py`.

G2D: este modulo consome exclusivamente o Execution Trace produzido por
`worker/cognitive_runner/runner.py::run_cognitive_core_with_trace()` - ja
NAO roda a cadeia do Core de novo (isso rodava a cadeia inteira DUAS vezes
por Job na G2C; o Runner foi adaptado, com aprovacao explicita, para reter
os objetos intermediarios de uma unica execucao e expo-los via trace). A
logica de contagem/tempo/explicabilidade abaixo e IDENTICA a da G2C - so
muda de onde os dados vem (trace ja computado, nao recomputado)."""
from __future__ import annotations

from worker.conviction.conviction_level import ConvictionLevel
from worker.timeline import event_types

_SATISFYING_LEVELS = (ConvictionLevel.STABLE, ConvictionLevel.STRONG)


def explain_no_decision(hypotheses, conviction_set, planning_set) -> str:
    """Primeira etapa que interrompeu o fluxo do segmento, na mesma ordem
    em que os dados atravessam o Core (Hypothesis -> Conviction ->
    Planning -> Decision). `Evaluation` nunca aparece aqui: `evaluate()`
    e uma funcao de caracterizacao pura que nunca filtra/rejeita uma
    Decision - toda DecisionSet gera exatamente uma EvaluationSet do
    mesmo tamanho ("total-join guarantee", `evaluation_set.py`) - ou
    seja, nesta versao do Core, Evaluation estruturalmente NUNCA pode ser
    a causa de "sem decisao"."""
    has_hypotheses = bool(hypotheses.track_hypotheses) or bool(hypotheses.entity_hypotheses)
    if not has_hypotheses:
        return "no_hypotheses"

    all_convictions = list(conviction_set.track_convictions.values()) + list(
        conviction_set.entity_convictions.values()
    )
    has_satisfying_conviction = any(c.level in _SATISFYING_LEVELS for c in all_convictions)
    if not has_satisfying_conviction:
        return "insufficient_conviction"

    has_plans = bool(planning_set.track_plans) or bool(planning_set.entity_plans)
    if not has_plans:
        return "planning_empty"

    return "decision_discarded"


def build_cognitive_report(trace: dict) -> dict:
    """Recebe o Execution Trace de `run_cognitive_core_with_trace()` e
    devolve `{"metrics": {...}, "summary": {...}}` - so dict/list,
    nenhuma dataclass nova."""
    raw = trace["raw_events"]
    derived = trace["derived_events"]
    frames = sum(1 for event in raw if event["event_type"] == event_types.FRAME_PROCESSED)

    memory_ms = working_state_ms = hypothesis_ms = 0.0
    conviction_ms = planning_ms = decision_ms = evaluation_ms = 0.0
    hypothesis_total = conviction_total = planning_total = 0
    decision_total = evaluation_total = 0
    segment_reports: list[dict] = []

    for entry in trace["segments"]:
        hypotheses = entry["hypotheses"]
        conviction_set = entry["conviction_set"]
        planning_set = entry["planning_set"]
        decision_set = entry["decision_set"]
        evaluation_set = entry["evaluation_set"]
        timing = entry["timing_ms"]

        memory_ms += timing["memory"]
        working_state_ms += timing["working_state"]
        hypothesis_ms += timing["hypothesis"]
        conviction_ms += timing["conviction"]
        planning_ms += timing["planning"]
        decision_ms += timing["decision"]
        evaluation_ms += timing["evaluation"]

        hyp_count = len(hypotheses.track_hypotheses) + len(hypotheses.entity_hypotheses)
        conv_count = len(conviction_set.track_convictions) + len(conviction_set.entity_convictions)
        plan_count = len(planning_set.track_plans) + len(planning_set.entity_plans)
        dec_count = len(decision_set.track_decisions) + len(decision_set.entity_decisions)
        eval_count = len(evaluation_set.track_evaluations) + len(evaluation_set.entity_evaluations)

        hypothesis_total += hyp_count
        conviction_total += conv_count
        planning_total += plan_count
        decision_total += dec_count
        evaluation_total += eval_count

        has_decision = dec_count > 0
        segment_reports.append(
            {
                "segment_id": entry["segment"].segment_id,
                "start_frame": entry["segment"].start_frame,
                "end_frame": entry["segment"].end_frame,
                "event_count": len(entry["segment_events"]),
                "hypothesis_count": hyp_count,
                "conviction_count": conv_count,
                "planning_count": plan_count,
                "decision_count": dec_count,
                "evaluation_count": eval_count,
                "has_decision": has_decision,
                "no_decision_reason": (
                    None if has_decision else explain_no_decision(hypotheses, conviction_set, planning_set)
                ),
            }
        )

    runner_total_ms = trace["timing_ms"]["execute_total"]

    metrics = {
        "counts": {
            "frames": frames,
            "timeline_events": len(raw),
            "derived_events": len(derived),
            "play_segments": len(trace["segments"]),
            "temporal_memories": len(trace["segments"]),
            "working_states": len(trace["segments"]),
            "hypothesis_count": hypothesis_total,
            "conviction_count": conviction_total,
            "planning_count": planning_total,
            "decision_count": decision_total,
            "evaluation_count": evaluation_total,
        },
        "timing_ms": {
            "timeline": trace["timing_ms"]["timeline"],
            "segmentation": trace["timing_ms"]["segmentation"],
            "enrichment": trace["timing_ms"]["enrichment"],
            "memory": memory_ms,
            "working_state": working_state_ms,
            "hypothesis": hypothesis_ms,
            "conviction": conviction_ms,
            "planning": planning_ms,
            "decision": decision_ms,
            "evaluation": evaluation_ms,
            "runner_total": runner_total_ms,
        },
        "segments": segment_reports,
    }

    total_segments = len(trace["segments"])
    segments_with_decision = sum(1 for s in segment_reports if s["has_decision"])
    segments_without_decision = total_segments - segments_with_decision

    summary = {
        "total_segments": total_segments,
        "segments_with_decision": segments_with_decision,
        "segments_without_decision": segments_without_decision,
        "decision_rate": (segments_with_decision / total_segments) if total_segments else 0.0,
        "total_time_ms": runner_total_ms,
        "average_time_ms_per_segment": (runner_total_ms / total_segments) if total_segments else 0.0,
    }

    return {"metrics": metrics, "summary": summary}
