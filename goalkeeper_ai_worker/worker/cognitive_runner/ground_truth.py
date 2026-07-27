"""evaluate_against_ground_truth: compara as decisoes do Cognitive Core com
um Ground Truth externo simples (Fase 3B, "Ground Truth Evaluation").

Esta sprint mede DESEMPENHO - nao altera comportamento nenhum. Nao
modifica nenhuma das 11 camadas do Cognitive Core, o Runner, o
BasicVisionEngine, o WorkerOrchestrator, nenhuma Stage nem o Pipeline
("NAO MODIFICAR" desta sprint inclui explicitamente Stages/Pipeline) - por
isso este modulo e standalone: nao e chamado por CognitiveRunnerStage.
Nao ha fonte real de Ground Truth em producao (sem banco, sem backend,
por escopo explicito desta sprint), entao nao faria sentido a Stage real
sempre mesclar `ground_truth_evaluation` vazio em todo Job. O uso previsto
e uma ferramenta/script de avaliacao offline (analogo a
`worker/explorers/cli.py`), que carrega um `cognitive_core_result` (de um
artifact.json ja processado) + um Ground Truth (dict/list) e chama esta
funcao diretamente.

Ground Truth (schema simples, sem dataclass): `list[{"segment_id": str,
"expected_action": str}]`. `predicted_action` e derivado do
`decision_set` de cada segmento em `cognitive_core_result` - se nenhuma
TrackDecision/EntityDecision existir, o segmento e rotulado "hold" (nao e
um PlanType do Core; e apenas o rotulo desta camada de avaliacao para
"nenhuma acao decidida"). Se houver mais de uma decisao no mesmo
segmento, usa-se a de menor `track_id` (ou, na ausencia de tracks, a
menor `entity` em ordem alfabetica) - simplificacao deliberada
("Ground Truth sera simples", enunciado desta sprint), documentada aqui
em vez de escondida.

Como `segment_id` e um `uuid4()` novo a cada execucao (G2A), um Ground
Truth so pode ser comparado contra o `cognitive_core_result` DA MESMA
execucao que gerou aqueles ids - nao e reutilizavel entre execucoes
diferentes do mesmo video."""
from __future__ import annotations

from collections import Counter

_NO_DECISION_ACTION = "hold"


def _predicted_action(result_entry: dict) -> str:
    decision_set = result_entry["decision_set"]
    track_decisions = decision_set.get("track_decisions") or {}
    entity_decisions = decision_set.get("entity_decisions") or {}

    if not track_decisions and not entity_decisions:
        return _NO_DECISION_ACTION
    if track_decisions:
        key = min(track_decisions, key=lambda k: int(k))
        return track_decisions[key]["plan_type"]
    key = min(entity_decisions)
    return entity_decisions[key]["plan_type"]


def _confusion_matrix(matched_segment_ids, expected_by_segment, predicted_by_segment) -> tuple[dict, list[str]]:
    classes = sorted(
        {expected_by_segment[sid] for sid in matched_segment_ids}
        | {predicted_by_segment[sid] for sid in matched_segment_ids}
    )
    matrix = {expected_class: {predicted_class: 0 for predicted_class in classes} for expected_class in classes}
    for segment_id in matched_segment_ids:
        matrix[expected_by_segment[segment_id]][predicted_by_segment[segment_id]] += 1
    return matrix, classes


def _rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def _precision_recall_f1(confusion_matrix: dict, classes: list[str]) -> tuple[dict, dict, dict]:
    precision: dict[str, float] = {}
    recall: dict[str, float] = {}
    f1_score: dict[str, float] = {}
    for cls in classes:
        true_positive = confusion_matrix[cls][cls]
        false_positive = sum(confusion_matrix[other][cls] for other in classes if other != cls)
        false_negative = sum(confusion_matrix[cls][other] for other in classes if other != cls)
        p = _rate(true_positive, true_positive + false_positive)
        r = _rate(true_positive, true_positive + false_negative)
        precision[cls] = p
        recall[cls] = r
        f1_score[cls] = _rate(2 * p * r, p + r)
    return precision, recall, f1_score


def _narrative(ground_truth: list[dict], total_matched: int, accuracy: float, wrong_predictions: list[dict]) -> str:
    if not ground_truth:
        return "Nenhum Ground Truth foi fornecido para avaliação."
    if total_matched == 0:
        return "Nenhum segmento do Ground Truth correspondeu a um segmento processado."

    accuracy_text = f"O modelo acertou {accuracy * 100:.0f}% das decisões."
    if not wrong_predictions:
        return accuracy_text

    pair_counts = Counter((record["expected_action"], record["predicted_action"]) for record in wrong_predictions)
    (expected, predicted), _ = max(pair_counts.items(), key=lambda item: item[1])
    return (
        f"{accuracy_text} A maior parte dos erros ocorreu por excesso de {predicted.upper()} "
        f"em situações onde o Ground Truth esperava {expected.upper()}."
    )


def evaluate_against_ground_truth(trace: dict, cognitive_core_result: list[dict], ground_truth: list[dict]) -> dict:
    """Compara `cognitive_core_result` (list[dict] ja produzido por
    run_cognitive_core()/run_cognitive_core_with_trace(), a mesma
    execucao que gerou `trace`) com `ground_truth` (list[{"segment_id",
    "expected_action"}]) e devolve metricas/relatorio/resumo - so
    dict/list, nenhuma dataclass nova."""
    expected_by_segment = {entry["segment_id"]: entry["expected_action"] for entry in ground_truth}
    predicted_by_segment = {entry["segment_id"]: _predicted_action(entry) for entry in cognitive_core_result}

    matched_segment_ids = sorted(set(expected_by_segment) & set(predicted_by_segment))
    missing_segment_ids = sorted(set(expected_by_segment) - set(predicted_by_segment))
    unexpected_segment_ids = sorted(set(predicted_by_segment) - set(expected_by_segment))

    correct_predictions: list[dict] = []
    wrong_predictions: list[dict] = []
    for segment_id in matched_segment_ids:
        expected = expected_by_segment[segment_id]
        predicted = predicted_by_segment[segment_id]
        record = {"segment_id": segment_id, "expected_action": expected, "predicted_action": predicted}
        (correct_predictions if expected == predicted else wrong_predictions).append(record)

    missing_predictions = [
        {"segment_id": sid, "expected_action": expected_by_segment[sid]} for sid in missing_segment_ids
    ]
    unexpected_predictions = [
        {"segment_id": sid, "predicted_action": predicted_by_segment[sid]} for sid in unexpected_segment_ids
    ]

    confusion_matrix, classes = _confusion_matrix(matched_segment_ids, expected_by_segment, predicted_by_segment)
    precision, recall, f1_score = _precision_recall_f1(confusion_matrix, classes)

    total_matched = len(matched_segment_ids)
    accuracy = _rate(len(correct_predictions), total_matched)

    return {
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "confusion_matrix": confusion_matrix,
        },
        "report": {
            "correct_predictions": correct_predictions,
            "wrong_predictions": wrong_predictions,
            "missing_predictions": missing_predictions,
            "unexpected_predictions": unexpected_predictions,
        },
        "summary": {
            "segments_in_execution": len(trace["segments"]),
            "segments_with_ground_truth": len(ground_truth),
            "segments_matched": total_matched,
            "narrative": _narrative(ground_truth, total_matched, accuracy, wrong_predictions),
        },
    }
