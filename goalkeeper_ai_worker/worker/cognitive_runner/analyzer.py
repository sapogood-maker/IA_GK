"""analyze_cognitive_quality: mede a QUALIDADE do raciocinio do Cognitive
Core sobre uma execucao real (Phase 3, "Cognitive Quality").

Esta sprint e EXCLUSIVAMENTE analitica: nao produz nenhuma decisao nova,
nao adiciona nenhuma heuristica de raciocinio, nao altera o comportamento
de nenhuma camada do Cognitive Core (congeladas desde o Architecture
Freeze v1.0), do Runner ou do Report (G2A-G2D). Este modulo apenas LE o
Execution Trace ja produzido por
`worker/cognitive_runner/runner.py::run_cognitive_core_with_trace()` (a
MESMA fonte de dados de `report.py`, G2C/G2D - nenhuma execucao adicional
do Core) e calcula indicadores sobre ele.

Todos os indicadores abaixo sao leituras diretas de campos JA existentes
nas dataclasses congeladas do Core (TrackConviction.consecutive_observations/
persistence_duration_seconds/state, PlaySegment.duration_seconds/events,
etc.) ou contagens/razoes derivadas deles - nenhum valor e inventado, nenhuma
regra nova decide nada sobre o video. O resultado e sempre dict/list."""
from __future__ import annotations

from statistics import mean

from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_state import ConvictionState
from worker.cognitive_runner.report import explain_no_decision

_SATISFYING_LEVELS = (ConvictionLevel.STABLE, ConvictionLevel.STRONG)

_BOTTLENECK_NARRATIVES = {
    "no_hypotheses": ("Hypothesis", "nenhuma hipótese ter sido formada a partir do estado observado"),
    "insufficient_conviction": ("Conviction", "ausência de observações suficientes para atingir STABLE"),
    "planning_empty": ("Planning", "nenhum plano ter sido gerado apesar de uma convicção satisfatória"),
    "decision_discarded": ("Decision", "todos os planos candidatos terem sido invalidados"),
}


def _has_satisfying_conviction(conviction_set) -> bool:
    all_convictions = list(conviction_set.track_convictions.values()) + list(
        conviction_set.entity_convictions.values()
    )
    return any(c.level in _SATISFYING_LEVELS for c in all_convictions)


def _segment_counts(trace: dict) -> dict:
    segments = trace["segments"]
    with_hypothesis = with_stable_conviction = with_decision = 0

    for entry in segments:
        hypotheses = entry["hypotheses"]
        if hypotheses.track_hypotheses or hypotheses.entity_hypotheses:
            with_hypothesis += 1
        if _has_satisfying_conviction(entry["conviction_set"]):
            with_stable_conviction += 1
        decision_set = entry["decision_set"]
        if decision_set.track_decisions or decision_set.entity_decisions:
            with_decision += 1

    total = len(segments)
    return {
        "segments_analyzed": total,
        "segments_with_hypothesis": with_hypothesis,
        "segments_without_hypothesis": total - with_hypothesis,
        "segments_with_stable_conviction": with_stable_conviction,
        "segments_with_decision": with_decision,
        "segments_without_decision": total - with_decision,
    }


def _rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def _conversion_rates(trace: dict) -> dict:
    """Taxa de conversao entre camadas consecutivas, medida em SEGMENTOS
    (nao em contagem bruta de objetos - ConvictionSet e cumulativo entre
    segmentos, entao dividir contagens agregadas produziria uma razao sem
    teto de 1.0). "Converteu" = o segmento avancou da condicao de uma
    etapa para a condicao satisfeita da proxima."""
    hypothesis_gate = hypothesis_to_stable_conviction = 0
    stable_conviction_gate = stable_conviction_to_planning = 0
    planning_gate = planning_to_decision = 0
    decision_gate = decision_to_evaluation = 0

    for entry in trace["segments"]:
        hypotheses = entry["hypotheses"]
        has_hypothesis = bool(hypotheses.track_hypotheses or hypotheses.entity_hypotheses)
        has_stable_conviction = _has_satisfying_conviction(entry["conviction_set"])
        planning_set = entry["planning_set"]
        has_planning = bool(planning_set.track_plans or planning_set.entity_plans)
        decision_set = entry["decision_set"]
        has_decision = bool(decision_set.track_decisions or decision_set.entity_decisions)
        evaluation_set = entry["evaluation_set"]
        has_evaluation = bool(evaluation_set.track_evaluations or evaluation_set.entity_evaluations)

        if has_hypothesis:
            hypothesis_gate += 1
            if has_stable_conviction:
                hypothesis_to_stable_conviction += 1
        if has_stable_conviction:
            stable_conviction_gate += 1
            if has_planning:
                stable_conviction_to_planning += 1
        if has_planning:
            planning_gate += 1
            if has_decision:
                planning_to_decision += 1
        if has_decision:
            decision_gate += 1
            if has_evaluation:
                decision_to_evaluation += 1

    return {
        "hypothesis_to_conviction": _rate(hypothesis_to_stable_conviction, hypothesis_gate),
        "conviction_to_planning": _rate(stable_conviction_to_planning, stable_conviction_gate),
        "planning_to_decision": _rate(planning_to_decision, planning_gate),
        "decision_to_evaluation": _rate(decision_to_evaluation, decision_gate),
    }


def _conviction_persistence(trace: dict) -> dict:
    """Le diretamente campos ja existentes de TrackConviction/EntityConviction
    (nenhum calculo novo sobre o Core): `persistence_duration_seconds` no
    momento em que `level` cruza para STABLE/STRONG pela primeira vez,
    `consecutive_observations` (maior sequencia de crescimento ja vista),
    `state == STRENGTHENED` (promocao - nivel subiu neste ciclo) e
    desaparecimentos de hypothesis_id entre um ConvictionSet e o seguinte
    (descarte - 2 faltas consecutivas, `_MAX_CONSECUTIVE_MISSES=1` no
    Core)."""
    segments = trace["segments"]

    time_to_stable: list[float] = []
    already_stable: set[str] = set()
    max_consecutive_observations = 0
    promoted_count = 0
    dropped_count = 0
    previous_ids: set[str] | None = None

    for entry in segments:
        conviction_set = entry["conviction_set"]
        all_convictions = list(conviction_set.track_convictions.items()) + list(
            conviction_set.entity_convictions.items()
        )
        current_ids = {hypothesis_id for hypothesis_id, _ in all_convictions}

        if previous_ids is not None:
            dropped_count += len(previous_ids - current_ids)
        previous_ids = current_ids

        for hypothesis_id, conviction in all_convictions:
            max_consecutive_observations = max(max_consecutive_observations, conviction.consecutive_observations)
            if conviction.state == ConvictionState.STRENGTHENED:
                promoted_count += 1
            if (
                conviction.level in _SATISFYING_LEVELS
                and hypothesis_id not in already_stable
                and conviction.persistence_duration_seconds is not None
            ):
                already_stable.add(hypothesis_id)
                time_to_stable.append(conviction.persistence_duration_seconds)

    return {
        "average_time_to_stable_seconds": mean(time_to_stable) if time_to_stable else None,
        "longest_growth_streak": max_consecutive_observations,
        "convictions_dropped": dropped_count,
        "convictions_promoted": promoted_count,
    }


def _temporal_analysis(trace: dict) -> dict:
    """`average_segment_duration_seconds` e a distribuicao de tamanhos
    usam `PlaySegment.duration_seconds`/`len(segment.events)` - campos ja
    calculados pelo Core (W30), nao recomputados aqui."""
    raw_events = trace["raw_events"]
    timestamps = sorted(event["timestamp_seconds"] for event in raw_events)
    deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]

    segments = trace["segments"]
    durations = [
        entry["segment"].duration_seconds for entry in segments if entry["segment"].duration_seconds is not None
    ]
    sizes = [len(entry["segment"].events) for entry in segments]

    return {
        "average_time_between_events_seconds": mean(deltas) if deltas else None,
        "average_segment_duration_seconds": mean(durations) if durations else None,
        "segment_size_distribution": {
            "min_events": min(sizes) if sizes else 0,
            "max_events": max(sizes) if sizes else 0,
            "mean_events": mean(sizes) if sizes else 0.0,
            "sizes": sizes,
        },
    }


def _summary(trace: dict) -> dict:
    segments = trace["segments"]
    total_segments = len(segments)

    bottleneck_distribution: dict[str, int] = {}
    for entry in segments:
        decision_set = entry["decision_set"]
        has_decision = bool(decision_set.track_decisions or decision_set.entity_decisions)
        if has_decision:
            continue
        reason = explain_no_decision(entry["hypotheses"], entry["conviction_set"], entry["planning_set"])
        bottleneck_distribution[reason] = bottleneck_distribution.get(reason, 0) + 1

    segments_without_decision = sum(bottleneck_distribution.values())
    primary_bottleneck = (
        max(bottleneck_distribution, key=lambda reason: bottleneck_distribution[reason])
        if bottleneck_distribution
        else None
    )

    if total_segments == 0:
        narrative = "Nenhum segmento foi analisado."
    elif segments_without_decision == 0:
        narrative = "Todas as jogadas analisadas produziram uma decisão."
    else:
        stage, reason_text = _BOTTLENECK_NARRATIVES[primary_bottleneck]
        proportion_word = "A maioria" if segments_without_decision > total_segments / 2 else "Parte"
        narrative = f"{proportion_word} das jogadas foi interrompida na etapa {stage} devido a {reason_text}."

    return {
        "bottleneck_distribution": bottleneck_distribution,
        "primary_bottleneck": primary_bottleneck,
        "narrative": narrative,
    }


def analyze_cognitive_quality(trace: dict) -> dict:
    """Recebe o Execution Trace de `run_cognitive_core_with_trace()` e
    devolve os indicadores de qualidade do raciocinio - so dict/list,
    nenhuma dataclass nova, nenhuma decisao alterada."""
    return {
        "segment_counts": _segment_counts(trace),
        "conversion_rates": _conversion_rates(trace),
        "conviction_persistence": _conviction_persistence(trace),
        "temporal_analysis": _temporal_analysis(trace),
        "summary": _summary(trace),
    }
