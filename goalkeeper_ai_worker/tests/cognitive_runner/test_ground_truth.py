"""Testes de worker.cognitive_runner.ground_truth.evaluate_against_ground_truth
(Fase 3B, "Ground Truth Evaluation"). Nao roda a cadeia real do Core -
`cognitive_core_result` e um `list[dict]` no MESMO formato exato que
`run_cognitive_core()`/`_segment_result()` produzem (a mesma disciplina de
`tests/pipeline/test_upload_artifact_stage.py`, que constroi fixtures de
artifact.json diretamente em dict/JSON em vez de rodar o engine inteiro) -
este modulo so opera sobre dict/list, nunca sobre dataclasses do Core."""
from __future__ import annotations

from worker.cognitive_runner.ground_truth import evaluate_against_ground_truth


def _result(segment_id: str, plan_type: str | None, track_id: int = 1) -> dict:
    if plan_type is None:
        decision_set = {"track_decisions": {}, "entity_decisions": {}, "observed_at_frame": 0, "observed_at_timestamp": 0.0}
    else:
        decision_set = {
            "track_decisions": {
                track_id: {
                    "track_id": track_id,
                    "selected_plan_id": f"{plan_type}:track:{track_id}",
                    "plan_type": plan_type,
                    "winning_criteria": ["only_candidate"],
                    "discarded_plan_ids": [],
                }
            },
            "entity_decisions": {},
            "observed_at_frame": 0,
            "observed_at_timestamp": 0.0,
        }
    return {
        "segment_id": segment_id,
        "start_frame": 0,
        "end_frame": 0,
        "decision_set": decision_set,
        "evaluation_set": {},
    }


def _trace(segment_count: int) -> dict:
    return {"segments": [object()] * segment_count}


def _gt(segment_id: str, expected_action: str) -> dict:
    return {"segment_id": segment_id, "expected_action": expected_action}


def test_accuracy_precision_recall_f1_and_confusion_matrix():
    """3x TP engage, 1x FN engage/FP hold, 1x TP hold - numeros escolhidos
    para que precision != recall em ambas as classes (evita mascarar uma
    troca de formula)."""
    results = [
        _result("s1", "engage"),
        _result("s2", "engage"),
        _result("s3", "engage"),
        _result("s4", "engage"),  # Ground Truth esperava "hold" - erro
        _result("s5", "hold"),
    ]
    ground_truth = [
        _gt("s1", "engage"),
        _gt("s2", "engage"),
        _gt("s3", "engage"),
        _gt("s4", "hold"),
        _gt("s5", "hold"),
    ]

    evaluation = evaluate_against_ground_truth(_trace(5), results, ground_truth)
    metrics = evaluation["metrics"]

    assert metrics["accuracy"] == 4 / 5
    assert metrics["precision"]["engage"] == 3 / 4  # 3 TP, 1 FP (s4)
    assert metrics["recall"]["engage"] == 3 / 3  # 3 TP, 0 FN
    assert metrics["precision"]["hold"] == 1 / 1  # 1 TP, 0 FP
    assert metrics["recall"]["hold"] == 1 / 2  # 1 TP, 1 FN (s4)
    assert metrics["f1_score"]["engage"] == 2 * 0.75 * 1.0 / (0.75 + 1.0)
    assert metrics["f1_score"]["hold"] == 2 * 1.0 * 0.5 / (1.0 + 0.5)
    assert metrics["confusion_matrix"] == {
        "engage": {"engage": 3, "hold": 0},
        "hold": {"engage": 1, "hold": 1},
    }


def test_report_lists_correct_and_wrong_predictions():
    results = [_result("s1", "engage"), _result("s2", "engage")]
    ground_truth = [_gt("s1", "engage"), _gt("s2", "hold")]

    evaluation = evaluate_against_ground_truth(_trace(2), results, ground_truth)
    report = evaluation["report"]

    assert report["correct_predictions"] == [
        {"segment_id": "s1", "expected_action": "engage", "predicted_action": "engage"},
    ]
    assert report["wrong_predictions"] == [
        {"segment_id": "s2", "expected_action": "hold", "predicted_action": "engage"},
    ]
    assert report["missing_predictions"] == []
    assert report["unexpected_predictions"] == []


def test_narrative_matches_the_accuracy_and_dominant_error():
    results = [
        _result("s1", "engage"), _result("s2", "engage"), _result("s3", "engage"),
        _result("s4", "engage"), _result("s5", "hold"),
    ]
    ground_truth = [
        _gt("s1", "engage"), _gt("s2", "engage"), _gt("s3", "engage"),
        _gt("s4", "hold"), _gt("s5", "hold"),
    ]

    evaluation = evaluate_against_ground_truth(_trace(5), results, ground_truth)

    assert evaluation["summary"]["narrative"] == (
        "O modelo acertou 80% das decisões. A maior parte dos erros ocorreu por "
        "excesso de ENGAGE em situações onde o Ground Truth esperava HOLD."
    )


def test_missing_prediction_when_ground_truth_references_an_unknown_segment():
    """'Predicao ausente': o Ground Truth aponta para um segment_id que
    nao existe em cognitive_core_result (ex.: o video foi reprocessado e
    os segment_ids mudaram, ou o segmento nunca existiu)."""
    results = [_result("s1", "engage")]
    ground_truth = [_gt("s1", "engage"), _gt("s-does-not-exist", "hold")]

    evaluation = evaluate_against_ground_truth(_trace(1), results, ground_truth)

    assert evaluation["report"]["missing_predictions"] == [
        {"segment_id": "s-does-not-exist", "expected_action": "hold"},
    ]
    assert evaluation["summary"]["segments_matched"] == 1


def test_unexpected_prediction_when_no_ground_truth_entry_exists_for_a_segment():
    """'Ground Truth ausente': o Core produziu um segmento sem nenhuma
    entrada correspondente no Ground Truth fornecido."""
    results = [_result("s1", "engage"), _result("s2", "hold")]
    ground_truth = [_gt("s1", "engage")]

    evaluation = evaluate_against_ground_truth(_trace(2), results, ground_truth)

    assert evaluation["report"]["unexpected_predictions"] == [
        {"segment_id": "s2", "predicted_action": "hold"},
    ]
    assert evaluation["summary"]["segments_matched"] == 1


def test_empty_ground_truth_produces_only_unexpected_predictions():
    results = [_result("s1", "engage"), _result("s2", None)]

    evaluation = evaluate_against_ground_truth(_trace(2), results, [])

    assert evaluation["metrics"]["accuracy"] == 0.0
    assert evaluation["metrics"]["confusion_matrix"] == {}
    assert len(evaluation["report"]["unexpected_predictions"]) == 2
    assert evaluation["report"]["missing_predictions"] == []
    assert evaluation["summary"]["narrative"] == "Nenhum Ground Truth foi fornecido para avaliação."


def test_empty_video_produces_only_missing_predictions():
    ground_truth = [_gt("s1", "engage"), _gt("s2", "hold")]

    evaluation = evaluate_against_ground_truth(_trace(0), [], ground_truth)

    assert evaluation["metrics"]["accuracy"] == 0.0
    assert len(evaluation["report"]["missing_predictions"]) == 2
    assert evaluation["report"]["unexpected_predictions"] == []
    assert evaluation["summary"]["segments_in_execution"] == 0
    assert evaluation["summary"]["narrative"] == (
        "Nenhum segmento do Ground Truth correspondeu a um segmento processado."
    )


def test_segment_without_any_decision_is_labeled_hold():
    results = [_result("s1", None)]
    ground_truth = [_gt("s1", "hold")]

    evaluation = evaluate_against_ground_truth(_trace(1), results, ground_truth)

    assert evaluation["report"]["correct_predictions"] == [
        {"segment_id": "s1", "expected_action": "hold", "predicted_action": "hold"},
    ]
    assert evaluation["metrics"]["accuracy"] == 1.0
