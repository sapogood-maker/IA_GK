"""Testes de worker.cognitive_runner.error_mining.analyze_cognitive_errors
(Fase 4A, "Cognitive Error Mining"). Categorias exercitadas via execucao
real do Core (NO_HYPOTHESIS/INSUFFICIENT_CONVICTION/WRONG_DECISION/
GROUND_TRUTH_MISMATCH) quando alcancaveis por um video sintetico simples;
PLANNING_EMPTY e o ramo UNKNOWN de "decision_discarded" sao estruturalmente
quase inalcancaveis por uma execucao real (mesmo achado ja documentado na
Fase 3 sobre `explain_no_decision`) - construidos com instancias REAIS das
dataclasses congeladas do Core (nunca mocks), a mesma disciplina ja usada
em tests/cognitive_runner/test_report.py."""
from __future__ import annotations

from uuid import uuid4

from worker.cognitive_runner.analyzer import analyze_cognitive_quality
from worker.cognitive_runner.error_mining import analyze_cognitive_errors
from worker.cognitive_runner.ground_truth import evaluate_against_ground_truth
from worker.cognitive_runner.runner import run_cognitive_core_with_trace
from worker.conviction.conviction_level import ConvictionLevel
from worker.conviction.conviction_set import ConvictionSet
from worker.conviction.conviction_state import ConvictionState
from worker.conviction.track_conviction import TrackConviction
from worker.decision.decision_set import DecisionSet
from worker.hypothesis.hypothesis_set import HypothesisSet
from worker.hypothesis.hypothesis_type import HypothesisType
from worker.hypothesis.track_hypothesis import TrackHypothesis
from worker.planning.plan_state import PlanState
from worker.planning.plan_type import PlanType
from worker.planning.planning_set import PlanningSet
from worker.planning.track_plan import TrackPlan
from worker.segments.play_segment import PlaySegment
from worker.timeline import event_types


def _event(event_type: str, frame_index: int, timestamp_seconds: float, metadata: dict | None = None) -> dict:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds,
        "track_id": 1,
        "entity": "person",
        "position": None,
        "confidence": None,
        "metadata": metadata or {},
        "parent_event_id": None,
    }


def _cluster(base_frame: int, start_timestamp: float) -> list[dict]:
    return [
        _event(event_types.FRAME_PROCESSED, base_frame, start_timestamp),
        _event(event_types.TRACK_STARTED, base_frame, start_timestamp),
        _event(event_types.OBJECT_STOPPED, base_frame + 1, start_timestamp + 0.05, metadata={"motion_state": "stopped"}),
        _event(event_types.TRACK_UPDATED, base_frame + 2, start_timestamp + 0.1),
    ]


def _three_segment_timeline() -> list[dict]:
    events: list[dict] = []
    for cluster_index, start_timestamp in enumerate((0.0, 10.0, 20.0)):
        events.extend(_cluster(base_frame=cluster_index * 100, start_timestamp=start_timestamp))
    return events


def _analyze(event_timeline: list[dict], build_ground_truth) -> dict:
    """`build_ground_truth(results) -> list[dict]` recebe os `results` da
    UNICA execucao usada nesta chamada - `segment_id` e um uuid4() novo a
    cada chamada de run_cognitive_core_with_trace() (G2A), entao o
    Ground Truth so pode ser construido a partir dos ids desta MESMA
    execucao, nunca de uma execucao separada."""
    results, trace = run_cognitive_core_with_trace(event_timeline)
    ground_truth = build_ground_truth(results)
    gt_evaluation = evaluate_against_ground_truth(trace, results, ground_truth)
    quality = analyze_cognitive_quality(trace)
    return analyze_cognitive_errors(trace, gt_evaluation, quality)


def _fake_segment_entry(segment_id: str, hypotheses, conviction_set, planning_set, decision_set) -> dict:
    segment = PlaySegment(
        segment_id=segment_id, start_frame=0, end_frame=0, start_timestamp=0.0, end_timestamp=0.0,
        duration_seconds=0.0, track_ids=frozenset({1}), ball_involved=False, events=[],
    )
    return {
        "segment": segment, "segment_events": [], "memory": None, "working_state": None,
        "hypotheses": hypotheses, "conviction_set": conviction_set, "planning_set": planning_set,
        "decision_set": decision_set, "evaluation_set": None, "timing_ms": {},
    }


def _stable_conviction_set() -> ConvictionSet:
    conviction = TrackConviction(
        hypothesis_id="stationary:track:1", hypothesis_type=HypothesisType.STATIONARY, track_id=1,
        consecutive_observations=3, lifetime_observations=3, missed_observations=0,
        first_observed_at_frame=0, first_observed_at_timestamp=0.0, persistence_duration_seconds=20.0,
        state=ConvictionState.STRENGTHENED, level=ConvictionLevel.STABLE,
    )
    return ConvictionSet(track_convictions={"stationary:track:1": conviction})


def _emerging_conviction_set() -> ConvictionSet:
    conviction = TrackConviction(
        hypothesis_id="stationary:track:1", hypothesis_type=HypothesisType.STATIONARY, track_id=1,
        consecutive_observations=1, lifetime_observations=1, missed_observations=0,
        first_observed_at_frame=0, first_observed_at_timestamp=0.0, persistence_duration_seconds=0.0,
        state=ConvictionState.BORN, level=ConvictionLevel.EMERGING,
    )
    return ConvictionSet(track_convictions={"stationary:track:1": conviction})


def _non_empty_hypotheses() -> HypothesisSet:
    hypothesis = TrackHypothesis(
        hypothesis_id="stationary:track:1", hypothesis_type=HypothesisType.STATIONARY, track_id=1,
        description="aparenta estar parado", evidence=(), matching_conditions=("motion_state_is_stopped",),
        support=1, origin="stationary",
    )
    return HypothesisSet(track_hypotheses=(hypothesis,))


def test_no_hypothesis_category():
    """Cluster sem nenhum evento de motion_state - nenhum producer de
    Hypothesis dispara (mesmo fixture da Fase 3)."""
    events = [_event(event_types.FRAME_PROCESSED, 0, 0.0), _event(event_types.TRACK_STARTED, 0, 0.0)]

    error_analysis = _analyze(
        events, lambda results: [{"segment_id": results[0]["segment_id"], "expected_action": "engage"}]
    )

    assert error_analysis["report"]["error_count"] == 1
    assert error_analysis["errors"][0]["category"] == "NO_HYPOTHESIS"


def test_insufficient_conviction_category():
    """1 unico segmento: hipotese existe, mas so 1 observacao consecutiva
    (EMERGING, limiar STABLE=3) - previsto "hold"."""
    events = _cluster(base_frame=0, start_timestamp=0.0)

    error_analysis = _analyze(
        events, lambda results: [{"segment_id": results[0]["segment_id"], "expected_action": "engage"}]
    )

    assert error_analysis["report"]["error_count"] == 1
    assert error_analysis["errors"][0]["category"] == "INSUFFICIENT_CONVICTION"


def test_wrong_decision_category():
    """3o segmento do fixture de 3 clusters produz uma decisao real
    ("engage") - Ground Truth espera "pursue", uma decisao real existiu
    mas nao bateu."""
    events = _three_segment_timeline()

    error_analysis = _analyze(
        events,
        lambda results: [
            {"segment_id": results[0]["segment_id"], "expected_action": "hold"},
            {"segment_id": results[1]["segment_id"], "expected_action": "hold"},
            {"segment_id": results[2]["segment_id"], "expected_action": "pursue"},
        ],
    )

    assert error_analysis["report"]["error_count"] == 1
    assert error_analysis["errors"][0]["category"] == "WRONG_DECISION"


def test_planning_empty_category_with_hand_built_core_objects():
    """PLANNING_EMPTY (Conviction satisfatoria, mas nenhum plano gerado) e
    estruturalmente quase inalcancavel hoje (todo HypothesisType tem
    PlanType mapeado, achado ja documentado na Fase 3) - construido
    diretamente com instancias REAIS das dataclasses congeladas (nunca
    mock), nao com uma execucao completa."""
    entry = _fake_segment_entry(
        "seg-1", _non_empty_hypotheses(), _stable_conviction_set(), PlanningSet(), DecisionSet(),
    )
    trace = {"segments": [entry]}
    gt_evaluation = {
        "report": {
            "wrong_predictions": [{"segment_id": "seg-1", "expected_action": "engage", "predicted_action": "hold"}],
            "missing_predictions": [],
            "unexpected_predictions": [],
        }
    }
    quality = {"segment_counts": {"segments_analyzed": 1}}

    error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)

    assert error_analysis["errors"][0]["category"] == "PLANNING_EMPTY"


def test_unknown_category_from_decision_discarded_with_hand_built_core_objects():
    """UNKNOWN cobre "decision_discarded" (plano existiu, mas Decision nao
    produziu nada) - tambem construido com dataclasses reais, ja que
    forcar esse caminho via uma execucao completa exigiria um cenario
    multi-segmento de invalidacao fora do escopo desta sprint."""
    planning_set = PlanningSet(
        track_plans={
            "engage:track:1": TrackPlan(
                plan_id="engage:track:1", plan_type=PlanType.ENGAGE, track_id=1,
                origin_conviction_id="stationary:track:1", satisfied_preconditions=("conviction_level_at_least_stable",),
                state=PlanState.EMERGED, objective="engajar o alvo parado",
            )
        }
    )
    entry = _fake_segment_entry(
        "seg-1", _non_empty_hypotheses(), _stable_conviction_set(), planning_set, DecisionSet(),
    )
    trace = {"segments": [entry]}
    gt_evaluation = {
        "report": {
            "wrong_predictions": [{"segment_id": "seg-1", "expected_action": "engage", "predicted_action": "hold"}],
            "missing_predictions": [],
            "unexpected_predictions": [],
        }
    }
    quality = {"segment_counts": {"segments_analyzed": 1}}

    error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)

    assert error_analysis["errors"][0]["category"] == "UNKNOWN"


def test_unknown_category_when_error_segment_is_missing_from_trace():
    """Fallback defensivo: um wrong_prediction referencia um segment_id
    que nao existe no Execution Trace."""
    trace = {"segments": []}
    gt_evaluation = {
        "report": {
            "wrong_predictions": [{"segment_id": "ghost", "expected_action": "engage", "predicted_action": "hold"}],
            "missing_predictions": [],
            "unexpected_predictions": [],
        }
    }
    quality = {"segment_counts": {"segments_analyzed": 0}}

    error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)

    assert error_analysis["errors"][0]["category"] == "UNKNOWN"


def test_ground_truth_mismatch_category_for_missing_and_unexpected_predictions():
    events = _three_segment_timeline()
    results, trace = run_cognitive_core_with_trace(events)
    ground_truth = [
        {"segment_id": results[0]["segment_id"], "expected_action": "hold"},  # correta, nao e erro
        {"segment_id": "segment-that-does-not-exist", "expected_action": "engage"},  # missing_prediction
    ]
    gt_evaluation = evaluate_against_ground_truth(trace, results[:1], ground_truth)  # so o 1o resultado
    quality = analyze_cognitive_quality(trace)

    error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)

    categories = {error["category"] for error in error_analysis["errors"]}
    assert categories == {"GROUND_TRUTH_MISMATCH"}
    assert error_analysis["report"]["error_count"] == 1


def test_video_without_errors_reports_zero_errors():
    events = _three_segment_timeline()

    error_analysis = _analyze(
        events,
        lambda results: [
            {"segment_id": results[0]["segment_id"], "expected_action": "hold"},
            {"segment_id": results[1]["segment_id"], "expected_action": "hold"},
            {"segment_id": results[2]["segment_id"], "expected_action": "engage"},
        ],
    )

    assert error_analysis["report"]["error_count"] == 0
    assert error_analysis["report"]["error_distribution"] == {}
    assert error_analysis["report"]["primary_error"] is None
    assert error_analysis["report"]["ranking"] == []
    assert error_analysis["summary"]["narrative"] == "Nenhum erro foi encontrado nesta execução."


def test_empty_video_and_empty_ground_truth_produce_zero_errors():
    error_analysis = _analyze([], lambda results: [])

    assert error_analysis["report"]["error_count"] == 0
    assert error_analysis["summary"]["segments_analyzed"] == 0
    assert error_analysis["summary"]["narrative"] == "Nenhum erro foi encontrado nesta execução."


def test_empty_ground_truth_on_a_non_empty_video_produces_ground_truth_mismatch_errors():
    events = _three_segment_timeline()

    error_analysis = _analyze(events, lambda results: [])

    assert error_analysis["report"]["error_count"] == 3
    assert error_analysis["report"]["primary_error"] == "GROUND_TRUTH_MISMATCH"
    assert all(error["category"] == "GROUND_TRUTH_MISMATCH" for error in error_analysis["errors"])


def test_ranking_orders_categories_by_count_descending_then_alphabetically():
    """3x NO_HYPOTHESIS (maior contagem - deve vir 1o), 2x
    INSUFFICIENT_CONVICTION e 2x GROUND_TRUTH_MISMATCH empatados (deve
    desempatar por ordem alfabetica: GROUND_TRUTH_MISMATCH antes de
    INSUFFICIENT_CONVICTION)."""
    empty_hypotheses = HypothesisSet()
    no_hypothesis_entries = [
        (f"no-hyp-{i}", _fake_segment_entry(f"no-hyp-{i}", empty_hypotheses, ConvictionSet(), PlanningSet(), DecisionSet()))
        for i in range(3)
    ]
    insufficient_conviction_entries = [
        (
            f"insuff-{i}",
            _fake_segment_entry(f"insuff-{i}", _non_empty_hypotheses(), _emerging_conviction_set(), PlanningSet(), DecisionSet()),
        )
        for i in range(2)
    ]

    trace = {"segments": [entry for _, entry in no_hypothesis_entries + insufficient_conviction_entries]}
    wrong_predictions = [
        {"segment_id": segment_id, "expected_action": "engage", "predicted_action": "hold"}
        for segment_id, _ in no_hypothesis_entries + insufficient_conviction_entries
    ]
    gt_evaluation = {
        "report": {
            "wrong_predictions": wrong_predictions,
            "missing_predictions": [
                {"segment_id": "m1", "expected_action": "engage"},
                {"segment_id": "m2", "expected_action": "engage"},
            ],
            "unexpected_predictions": [],
        }
    }
    quality = {"segment_counts": {"segments_analyzed": len(trace["segments"])}}

    error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)

    assert error_analysis["report"]["error_distribution"] == {
        "NO_HYPOTHESIS": 3, "INSUFFICIENT_CONVICTION": 2, "GROUND_TRUTH_MISMATCH": 2,
    }
    assert error_analysis["report"]["ranking"] == [
        {"category": "NO_HYPOTHESIS", "count": 3},
        {"category": "GROUND_TRUTH_MISMATCH", "count": 2},
        {"category": "INSUFFICIENT_CONVICTION", "count": 2},
    ]
    assert error_analysis["report"]["primary_error"] == "NO_HYPOTHESIS"
