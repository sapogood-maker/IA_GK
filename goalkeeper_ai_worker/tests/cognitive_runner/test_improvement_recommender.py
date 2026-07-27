"""Testes de worker.cognitive_runner.improvement_recommender.recommend_improvements
(Fase 4B). Este modulo opera exclusivamente sobre os dicts ja produzidos
pelas fases anteriores (Cognitive Quality/Ground Truth Evaluation/
Cognitive Error Analysis) - nao precisa de nenhuma dataclass do Core, so
dict/list, entao os fixtures aqui sao construidos diretamente (mesma
disciplina de tests/pipeline/test_upload_artifact_stage.py)."""
from __future__ import annotations

from worker.cognitive_runner.improvement_recommender import recommend_improvements


def _trace(segment_count: int) -> dict:
    return {"segments": [object()] * segment_count}


def _quality(
    segments_analyzed: int = 0,
    segments_with_hypothesis: int = 0,
    segments_without_hypothesis: int = 0,
    segments_with_stable_conviction: int = 0,
    hypothesis_to_conviction: float = 1.0,
    conviction_to_planning: float = 1.0,
) -> dict:
    return {
        "segment_counts": {
            "segments_analyzed": segments_analyzed,
            "segments_with_hypothesis": segments_with_hypothesis,
            "segments_without_hypothesis": segments_without_hypothesis,
            "segments_with_stable_conviction": segments_with_stable_conviction,
        },
        "conversion_rates": {
            "hypothesis_to_conviction": hypothesis_to_conviction,
            "conviction_to_planning": conviction_to_planning,
        },
    }


def _gt_evaluation(segments_matched: int) -> dict:
    return {"summary": {"segments_matched": segments_matched}}


def _error_analysis(error_distribution: dict[str, int]) -> dict:
    return {"report": {"error_distribution": error_distribution, "error_count": sum(error_distribution.values())}}


def test_no_recommendation_when_there_is_no_evidence_at_all():
    trace = _trace(5)
    quality = _quality(
        segments_analyzed=5, segments_with_hypothesis=5, segments_without_hypothesis=0,
        segments_with_stable_conviction=5, hypothesis_to_conviction=1.0, conviction_to_planning=1.0,
    )
    gt_evaluation = _gt_evaluation(5)
    error_analysis = _error_analysis({})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert result["improvement_candidates"] == []
    assert result["summary"]["narrative"] == "Nenhuma oportunidade de melhoria foi identificada nesta execução."


def test_single_dominant_layer_gets_priority_one():
    trace = _trace(10)
    quality = _quality(
        segments_analyzed=10, segments_with_hypothesis=10, segments_without_hypothesis=0,
        segments_with_stable_conviction=10, hypothesis_to_conviction=1.0, conviction_to_planning=1.0,
    )
    gt_evaluation = _gt_evaluation(10)  # >= _MIN_SAMPLE_SIZE - sem desconto por amostra
    error_analysis = _error_analysis({"INSUFFICIENT_CONVICTION": 10})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert len(result["improvement_candidates"]) == 1
    candidate = result["improvement_candidates"][0]
    assert candidate["layer"] == "CONVICTION"
    assert candidate["priority"] == 1
    assert candidate["confidence"] == 1.0
    assert candidate["reason"] == "Responsável por 100% dos erros observados."
    assert "Conviction" in result["summary"]["narrative"]


def test_tie_between_layers_breaks_alphabetically():
    trace = _trace(10)
    quality = _quality(segments_analyzed=10, segments_with_hypothesis=10, segments_with_stable_conviction=10)
    gt_evaluation = _gt_evaluation(10)
    error_analysis = _error_analysis({"NO_HYPOTHESIS": 5, "INSUFFICIENT_CONVICTION": 5})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)
    candidates = result["improvement_candidates"]

    assert [c["layer"] for c in candidates] == ["CONVICTION", "HYPOTHESIS"]  # C antes de H
    assert candidates[0]["confidence"] == candidates[1]["confidence"] == 0.5
    assert [c["priority"] for c in candidates] == [1, 2]


def test_ground_truth_empty_recommends_ground_truth_layer_without_sample_discount():
    """Sem nenhum segmento comparavel (segments_matched=0), todo predicao
    vira GROUND_TRUTH_MISMATCH - o desconto por amostra NAO se aplica a
    essa camada (a propria causa do erro E ter poucos/nenhum segmento
    comparavel)."""
    trace = _trace(3)
    quality = _quality(segments_analyzed=3, segments_with_hypothesis=3, segments_with_stable_conviction=1)
    gt_evaluation = _gt_evaluation(0)
    error_analysis = _error_analysis({"GROUND_TRUTH_MISMATCH": 3})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert len(result["improvement_candidates"]) == 1
    candidate = result["improvement_candidates"][0]
    assert candidate["layer"] == "GROUND_TRUTH"
    assert candidate["confidence"] == 1.0  # nao descontado, mesmo com segments_matched=0


def test_empty_video_produces_no_recommendations():
    trace = _trace(0)
    quality = _quality()
    gt_evaluation = _gt_evaluation(0)
    error_analysis = _error_analysis({})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert result["improvement_candidates"] == []
    assert result["summary"]["segments_analyzed"] == 0


def test_unknown_layer_is_recommended_when_present():
    trace = _trace(4)
    quality = _quality(segments_analyzed=4, segments_with_hypothesis=4, segments_with_stable_conviction=4)
    gt_evaluation = _gt_evaluation(4)
    error_analysis = _error_analysis({"UNKNOWN": 4})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert len(result["improvement_candidates"]) == 1
    assert result["improvement_candidates"][0]["layer"] == "UNKNOWN"


def test_priority_ordering_matches_descending_confidence():
    trace = _trace(20)
    quality = _quality(segments_analyzed=20, segments_with_hypothesis=20, segments_with_stable_conviction=20)
    gt_evaluation = _gt_evaluation(20)
    error_analysis = _error_analysis({"INSUFFICIENT_CONVICTION": 10, "WRONG_DECISION": 6, "NO_HYPOTHESIS": 4})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)
    candidates = result["improvement_candidates"]

    assert [c["layer"] for c in candidates] == ["CONVICTION", "DECISION", "HYPOTHESIS"]
    assert [c["priority"] for c in candidates] == [1, 2, 3]
    assert [c["confidence"] for c in candidates] == [0.5, 0.3, 0.2]


def test_quality_only_evidence_produces_a_discounted_candidate_when_there_are_no_errors():
    """Sem nenhum erro confirmado pelo Ground Truth, mas com uma taxa real
    de conversao baixa (Fase 3) - o candidato ainda aparece, com
    confidence descontada (evidencia mais fraca, nao confirmada)."""
    trace = _trace(10)
    quality = _quality(
        segments_analyzed=10, segments_with_hypothesis=10, segments_without_hypothesis=0,
        segments_with_stable_conviction=4, hypothesis_to_conviction=0.4, conviction_to_planning=1.0,
    )
    gt_evaluation = _gt_evaluation(10)
    error_analysis = _error_analysis({})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    assert len(result["improvement_candidates"]) == 1
    candidate = result["improvement_candidates"][0]
    assert candidate["layer"] == "CONVICTION"
    assert candidate["confidence"] == (1.0 - 0.4) * 0.5  # deficiencia * _QUALITY_DISCOUNT
    assert "ainda sem confirmação do Ground Truth" in candidate["reason"]


def test_small_ground_truth_sample_discounts_confidence_for_core_layers():
    trace = _trace(2)
    quality = _quality(segments_analyzed=2, segments_with_hypothesis=2, segments_with_stable_conviction=2)
    gt_evaluation = _gt_evaluation(2)  # < _MIN_SAMPLE_SIZE (5) - fator 2/5 = 0.4
    error_analysis = _error_analysis({"INSUFFICIENT_CONVICTION": 2})

    result = recommend_improvements(trace, quality, gt_evaluation, error_analysis)

    candidate = result["improvement_candidates"][0]
    assert candidate["confidence"] == 1.0 * (2 / 5)
