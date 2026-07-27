"""analyze_cognitive_errors: para cada erro encontrado pelo Ground Truth
Evaluation (Fase 3B), localiza a PRIMEIRA camada do Cognitive Core
responsavel por ele (Fase 4A, "Cognitive Error Mining").

Esta sprint classifica erros - nunca corrige, nunca altera, nunca produz
uma decisao nova. Nao modifica nenhuma das 11 camadas do Cognitive Core,
o Runner, o WorkerOrchestrator, nenhuma Stage nem o Pipeline. Como
`evaluate_against_ground_truth` (Fase 3B), este modulo e standalone -
"NAO MODIFICAR" desta sprint inclui explicitamente Stages/Pipeline, e nao
ha Ground Truth real em producao.

Reutiliza `worker.cognitive_runner.report.explain_no_decision` (Fase 3) -
a mesma classificacao de "primeira etapa que interrompeu o fluxo" ja
usada para segmentos SEM decisao e reaproveitada aqui, em vez de
duplicada, para decidir a categoria de um erro cujo predicted_action foi
"hold" (nenhuma decisao real produzida).

Categorias (exatamente as 6 do enunciado desta sprint):
- NO_HYPOTHESIS: nenhuma hipotese se formou no segmento.
- INSUFFICIENT_CONVICTION: hipotese existiu, mas nenhuma Conviction
  atingiu STABLE/STRONG.
- PLANNING_EMPTY: Conviction satisfatoria existiu, mas nenhum plano foi
  gerado (hoje estruturalmente raro no Core - todo HypothesisType tem
  PlanType mapeado - mas o codigo cobre o caso defensivamente, como o
  proprio `explain_no_decision` ja fazia na Fase 3).
- WRONG_DECISION: o Core produziu uma decisao real (predicted_action e
  um PlanType, nao "hold"), mas ela nao bateu com o Ground Truth.
- GROUND_TRUTH_MISMATCH: o segmento do Ground Truth nao foi encontrado na
  execucao, ou vice-versa (`missing_predictions`/`unexpected_predictions`
  de `evaluate_against_ground_truth`) - nao e um erro de raciocinio do
  Core, e uma divergencia estrutural entre o Ground Truth e a execucao
  (ex.: `segment_id` de uma execucao anterior, ja nao-deterministico
  entre execucoes, G2A).
- UNKNOWN: fallback - cobre o caso "decision_discarded" de
  `explain_no_decision` (planos existiram, mas `decide()` descartou todos
  os candidatos por invalidacao - nao se encaixa nas 4 categorias de
  camada acima) e qualquer segmento referenciado por um erro que nao
  exista no Execution Trace (defensivo)."""
from __future__ import annotations

from worker.cognitive_runner.report import explain_no_decision

_REASON_TO_CATEGORY = {
    "no_hypotheses": "NO_HYPOTHESIS",
    "insufficient_conviction": "INSUFFICIENT_CONVICTION",
    "planning_empty": "PLANNING_EMPTY",
    "decision_discarded": "UNKNOWN",
}

_CATEGORY_LABELS = {
    "NO_HYPOTHESIS": "ausência de hipótese",
    "INSUFFICIENT_CONVICTION": "Conviction insuficiente",
    "PLANNING_EMPTY": "Planning vazio",
    "WRONG_DECISION": "decisão incorreta",
    "GROUND_TRUTH_MISMATCH": "divergência com o Ground Truth",
    "UNKNOWN": "causa não identificada",
}

# Categorias cuja causa-raiz ocorre ANTES da etapa Planning (Hypothesis/
# Conviction) - usado no resumo textual ("X% dos erros ocorreram antes
# da etapa Planning").
_BEFORE_PLANNING_CATEGORIES = {"NO_HYPOTHESIS", "INSUFFICIENT_CONVICTION"}


def _segment_entries_by_id(trace: dict) -> dict:
    return {entry["segment"].segment_id: entry for entry in trace["segments"]}


def _classify_wrong_decision(entry: dict | None) -> str:
    if entry is None:
        return "UNKNOWN"

    decision_set = entry["decision_set"]
    has_decision = bool(decision_set.track_decisions or decision_set.entity_decisions)
    if has_decision:
        return "WRONG_DECISION"

    reason = explain_no_decision(entry["hypotheses"], entry["conviction_set"], entry["planning_set"])
    return _REASON_TO_CATEGORY[reason]


def _ranking(error_distribution: dict[str, int]) -> list[dict]:
    return [
        {"category": category, "count": count}
        for category, count in sorted(error_distribution.items(), key=lambda item: (-item[1], item[0]))
    ]


def _narrative(error_count: int, primary_error: str | None, before_planning_rate: float) -> str:
    if error_count == 0:
        return "Nenhum erro foi encontrado nesta execução."

    primary_label = _CATEGORY_LABELS[primary_error]
    return (
        f"A maior parte dos erros foi causada por {primary_label}. "
        f"{before_planning_rate * 100:.0f}% dos erros ocorreram antes da etapa Planning."
    )


def analyze_cognitive_errors(trace: dict, ground_truth_evaluation: dict, quality: dict) -> dict:
    """Recebe o Execution Trace, a saida de
    `evaluate_against_ground_truth()` (Fase 3B) e a saida de
    `analyze_cognitive_quality()` (Fase 3) - so dict/list, nenhuma
    dataclass nova, nenhuma decisao alterada."""
    entries_by_segment = _segment_entries_by_id(trace)
    gt_report = ground_truth_evaluation["report"]

    errors: list[dict] = []
    for record in gt_report["wrong_predictions"]:
        entry = entries_by_segment.get(record["segment_id"])
        errors.append({**record, "category": _classify_wrong_decision(entry)})

    for record in gt_report["missing_predictions"] + gt_report["unexpected_predictions"]:
        errors.append({**record, "category": "GROUND_TRUTH_MISMATCH"})

    error_distribution: dict[str, int] = {}
    for error in errors:
        error_distribution[error["category"]] = error_distribution.get(error["category"], 0) + 1

    error_count = len(errors)
    ranking = _ranking(error_distribution)
    primary_error = ranking[0]["category"] if ranking else None

    before_planning_count = sum(
        count for category, count in error_distribution.items() if category in _BEFORE_PLANNING_CATEGORIES
    )
    before_planning_rate = (before_planning_count / error_count) if error_count else 0.0

    return {
        "errors": errors,
        "report": {
            "error_count": error_count,
            "error_distribution": error_distribution,
            "primary_error": primary_error,
            "ranking": ranking,
        },
        "summary": {
            "segments_analyzed": quality["segment_counts"]["segments_analyzed"],
            "before_planning_rate": before_planning_rate,
            "narrative": _narrative(error_count, primary_error, before_planning_rate),
        },
    }
