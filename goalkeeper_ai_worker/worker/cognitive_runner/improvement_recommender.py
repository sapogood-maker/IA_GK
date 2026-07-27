"""recommend_improvements: usa exclusivamente os resultados ja produzidos
pelas fases anteriores (Cognitive Quality, Ground Truth Evaluation,
Cognitive Error Analysis) para RANQUEAR quais camadas do Cognitive Core
representam a maior oportunidade de melhoria (Fase 4B, "Cognitive
Improvement Recommender").

Esta sprint NAO melhora o Core, NAO altera nenhuma decisao e NAO cria
heuristica alguma que influencie o raciocinio - ela so LE metricas ja
calculadas e produz uma recomendacao de PRIORIDADE (onde um humano deveria
olhar primeiro). Standalone, como `ground_truth.py` (Fase 3B) e
`error_mining.py` (Fase 4A): nao e chamado por CognitiveRunnerStage/
Pipeline (fora do escopo desta sprint).

Camadas analisadas (`_LAYERS`): HYPOTHESIS, CONVICTION, PLANNING,
DECISION, GROUND_TRUTH, UNKNOWN - as mesmas 6 categorias de
`error_mining.py`, so sem o prefixo de motivo (`NO_HYPOTHESIS` ->
`HYPOTHESIS`, `INSUFFICIENT_CONVICTION` -> `CONVICTION`,
`PLANNING_EMPTY` -> `PLANNING`, `WRONG_DECISION` -> `DECISION`,
`GROUND_TRUTH_MISMATCH` -> `GROUND_TRUTH`, `UNKNOWN` -> `UNKNOWN`).

Cada candidato reune DUAS fontes de evidencia possiveis, nunca inventadas:

1. Evidencia por ERRO (Ground Truth): a fracao dos erros de
   `error_mining.py` atribuidos aquela camada
   (`error_count(camada) / total_errors`). E a evidencia mais forte -
   confirmada por comparacao com Ground Truth real.
2. Evidencia por QUALIDADE (Cognitive Quality, so para HYPOTHESIS/
   CONVICTION/PLANNING - DECISION nao tem uma taxa de conversao util para
   isso, ja que `decide()` produz uma decisao para qualquer candidato nao
   invalidado, W37): uma taxa de "deficiencia" (1 - taxa de conversao real
   da Fase 3) quando a camada anterior teve oportunidade real de
   converter (ex.: CONVICTION so e avaliada se houve pelo menos 1
   segmento com hipotese). Mais fraca - nao confirmada por Ground Truth,
   por isso sofre um desconto fixo (`_QUALITY_DISCOUNT = 0.5`).

Quando ambas existem para uma camada, a evidencia por erro prevalece (e
estritamente mais forte); a evidencia por qualidade so aparece quando NAO
ha erro algum atribuido aquela camada (ela adiciona informacao nova, em
vez de duplicar).

Desconto por tamanho de amostra: `confidence` das camadas do Core
(HYPOTHESIS/CONVICTION/PLANNING/DECISION) baseadas em erro e multiplicada
por `min(1.0, segments_matched / _MIN_SAMPLE_SIZE)` - poucos segmentos
comparados contra o Ground Truth (`evaluate_against_ground_truth`,
Fase 3B) tornam a conclusao menos confiavel, mesmo que a fracao de erros
seja alta. NAO se aplica a GROUND_TRUTH/UNKNOWN: a propria existencia de
GROUND_TRUTH_MISMATCH JA significa "poucos/nenhum segmento comparavel" -
descontar por essa mesma causa anularia o sinal."""
from __future__ import annotations

_LAYERS = ("HYPOTHESIS", "CONVICTION", "PLANNING", "DECISION", "GROUND_TRUTH", "UNKNOWN")

_LAYER_FOR_ERROR_CATEGORY = {
    "NO_HYPOTHESIS": "HYPOTHESIS",
    "INSUFFICIENT_CONVICTION": "CONVICTION",
    "PLANNING_EMPTY": "PLANNING",
    "WRONG_DECISION": "DECISION",
    "GROUND_TRUTH_MISMATCH": "GROUND_TRUTH",
    "UNKNOWN": "UNKNOWN",
}

_SAMPLE_DISCOUNTED_LAYERS = {"HYPOTHESIS", "CONVICTION", "PLANNING", "DECISION"}
_MIN_SAMPLE_SIZE = 5

_QUALITY_DISCOUNT = 0.5

_QUALITY_DEFICIENCY_DESCRIPTION = {
    "HYPOTHESIS": "dos segmentos analisados não formaram nenhuma hipótese",
    "CONVICTION": "das hipóteses observadas não evoluíram para uma convicção estável",
    "PLANNING": "das convicções estáveis não geraram nenhum plano",
}

_LAYER_LABELS = {
    "HYPOTHESIS": "Hypothesis",
    "CONVICTION": "Conviction",
    "PLANNING": "Planning",
    "DECISION": "Decision",
    "GROUND_TRUTH": "Ground Truth",
    "UNKNOWN": "desconhecida",
}


def _error_counts_by_layer(error_analysis: dict) -> tuple[dict[str, int], int]:
    layer_counts: dict[str, int] = {}
    for category, count in error_analysis["report"]["error_distribution"].items():
        layer = _LAYER_FOR_ERROR_CATEGORY.get(category, "UNKNOWN")
        layer_counts[layer] = layer_counts.get(layer, 0) + count
    return layer_counts, error_analysis["report"]["error_count"]


def _quality_deficiency(layer: str, quality: dict) -> tuple[float, dict] | None:
    """Devolve (taxa_de_deficiencia, metricas) so quando a camada ANTERIOR
    teve oportunidade real de converter - evita reportar "100% de
    deficiencia" quando o denominador real era 0 (ex.: nao ha segmento
    com convicção estável para culpar Planning por nada)."""
    segment_counts = quality["segment_counts"]
    conversion_rates = quality["conversion_rates"]

    if layer == "HYPOTHESIS":
        segments_analyzed = segment_counts["segments_analyzed"]
        if segments_analyzed == 0:
            return None
        rate = segment_counts["segments_without_hypothesis"] / segments_analyzed
        metrics = {
            "segments_without_hypothesis": segment_counts["segments_without_hypothesis"],
            "segments_analyzed": segments_analyzed,
            "deficiency_rate": rate,
        }
        return (rate, metrics) if rate > 0 else None

    if layer == "CONVICTION":
        if segment_counts["segments_with_hypothesis"] == 0:
            return None
        rate = 1.0 - conversion_rates["hypothesis_to_conviction"]
        metrics = {"hypothesis_to_conviction": conversion_rates["hypothesis_to_conviction"], "deficiency_rate": rate}
        return (rate, metrics) if rate > 0 else None

    if layer == "PLANNING":
        if segment_counts["segments_with_stable_conviction"] == 0:
            return None
        rate = 1.0 - conversion_rates["conviction_to_planning"]
        metrics = {"conviction_to_planning": conversion_rates["conviction_to_planning"], "deficiency_rate": rate}
        return (rate, metrics) if rate > 0 else None

    return None


def _narrative(candidates: list[dict]) -> str:
    if not candidates:
        return "Nenhuma oportunidade de melhoria foi identificada nesta execução."
    top = candidates[0]
    layer_label = _LAYER_LABELS[top["layer"]]
    return (
        f"As análises indicam que a camada {layer_label} representa a maior oportunidade de melhoria. "
        f"{top['reason']}"
    )


def recommend_improvements(
    trace: dict, quality: dict, ground_truth_evaluation: dict, error_analysis: dict
) -> dict:
    """Recebe o Execution Trace, `analyze_cognitive_quality()` (Fase 3),
    `evaluate_against_ground_truth()` (Fase 3B) e `analyze_cognitive_errors()`
    (Fase 4A) e devolve `{"improvement_candidates": [...], "summary": {...}}`
    - so dict/list, nenhuma dataclass nova, nenhuma decisao do Core lida ou
    alterada."""
    layer_error_counts, total_errors = _error_counts_by_layer(error_analysis)
    segments_matched = ground_truth_evaluation["summary"]["segments_matched"]
    sample_factor = min(1.0, segments_matched / _MIN_SAMPLE_SIZE)

    candidates: list[dict] = []
    for layer in _LAYERS:
        error_count = layer_error_counts.get(layer, 0)
        error_share = (error_count / total_errors) if total_errors else 0.0

        if error_share > 0:
            factor = sample_factor if layer in _SAMPLE_DISCOUNTED_LAYERS else 1.0
            confidence = error_share * factor
            reason = f"Responsável por {error_share * 100:.0f}% dos erros observados."
            supporting_metrics = {
                "error_count": error_count,
                "total_errors": total_errors,
                "error_share": error_share,
                "segments_matched": segments_matched,
            }
        else:
            deficiency = _quality_deficiency(layer, quality)
            if deficiency is None:
                continue
            rate, supporting_metrics = deficiency
            confidence = rate * _QUALITY_DISCOUNT
            reason = f"{rate * 100:.0f}% {_QUALITY_DEFICIENCY_DESCRIPTION[layer]}, ainda sem confirmação do Ground Truth."

        if confidence > 0:
            candidates.append(
                {"layer": layer, "confidence": confidence, "reason": reason, "supporting_metrics": supporting_metrics}
            )

    candidates.sort(key=lambda c: (-c["confidence"], c["layer"]))
    improvement_candidates = [
        {
            "layer": candidate["layer"],
            "priority": index,
            "confidence": candidate["confidence"],
            "reason": candidate["reason"],
            "supporting_metrics": candidate["supporting_metrics"],
        }
        for index, candidate in enumerate(candidates, start=1)
    ]

    return {
        "improvement_candidates": improvement_candidates,
        "summary": {
            "segments_analyzed": len(trace["segments"]),
            "narrative": _narrative(improvement_candidates),
        },
    }
