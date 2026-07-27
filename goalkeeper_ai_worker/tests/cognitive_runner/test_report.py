"""Testes de worker.cognitive_runner.report.build_cognitive_report (Phase 2,
G2C/G2D) - observabilidade/explicabilidade. Nao mocka nenhuma camada do
Cognitive Core - roda a cadeia real, igual a tests/cognitive_runner/
test_runner.py (fixtures deliberadamente equivalentes, mesma disciplina de
"real Timeline sintetica").

G2D: build_cognitive_report() consome o Execution Trace, nao mais o
event_timeline diretamente - `_report_for()` roda a cadeia real UMA VEZ
via run_cognitive_core_with_trace() e repassa o trace."""
from __future__ import annotations

from uuid import uuid4

from worker.cognitive_runner.report import build_cognitive_report
from worker.cognitive_runner.runner import run_cognitive_core_with_trace
from worker.timeline import event_types


def _report_for(event_timeline: list[dict]) -> dict:
    _, trace = run_cognitive_core_with_trace(event_timeline)
    return build_cognitive_report(trace)


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
    """Mesma receita de tests/cognitive_runner/test_runner.py: 3 clusters
    do mesmo track_id=1 parado, separados por ~10s (> 1.0s, limiar da
    GapStrategy) - o 3o segmento cruza o limiar STABLE (3 observacoes
    consecutivas) e produz decisao; os 2 primeiros nao."""
    events: list[dict] = []
    for cluster_index, start_timestamp in enumerate((0.0, 10.0, 20.0)):
        events.extend(_cluster(base_frame=cluster_index * 100, start_timestamp=start_timestamp))
    return events


_METRIC_COUNT_KEYS = {
    "frames", "timeline_events", "derived_events", "play_segments", "temporal_memories",
    "working_states", "hypothesis_count", "conviction_count", "planning_count",
    "decision_count", "evaluation_count",
}
_METRIC_TIMING_KEYS = {
    "timeline", "segmentation", "enrichment", "memory", "working_state", "hypothesis",
    "conviction", "planning", "decision", "evaluation", "runner_total",
}
_SEGMENT_KEYS = {
    "segment_id", "start_frame", "end_frame", "event_count", "hypothesis_count",
    "conviction_count", "planning_count", "decision_count", "evaluation_count",
    "has_decision", "no_decision_reason",
}
_SUMMARY_KEYS = {
    "total_segments", "segments_with_decision", "segments_without_decision",
    "decision_rate", "total_time_ms", "average_time_ms_per_segment",
}


def test_report_shape_is_plain_dict_list_with_no_new_dataclasses():
    report = _report_for(_three_segment_timeline())

    assert set(report.keys()) == {"metrics", "summary"}
    assert isinstance(report["metrics"], dict)
    assert isinstance(report["summary"], dict)
    assert set(report["metrics"].keys()) == {"counts", "timing_ms", "segments"}
    assert set(report["metrics"]["counts"].keys()) == _METRIC_COUNT_KEYS
    assert set(report["metrics"]["timing_ms"].keys()) == _METRIC_TIMING_KEYS
    assert isinstance(report["metrics"]["segments"], list)
    assert set(report["summary"].keys()) == _SUMMARY_KEYS


def test_counts_are_correct_for_three_segments():
    report = _report_for(_three_segment_timeline())
    counts = report["metrics"]["counts"]

    assert counts["frames"] == 3  # um FRAME_PROCESSED por cluster
    assert counts["play_segments"] == 3
    assert counts["temporal_memories"] == 3
    assert counts["working_states"] == 3
    assert counts["timeline_events"] == 12  # 3 clusters * 4 eventos brutos
    # 1 hipotese (stationary) por segmento, nunca 0 neste fixture
    assert counts["hypothesis_count"] == 3


def test_timings_are_valid_non_negative_numbers_and_runner_total_is_the_largest():
    report = _report_for(_three_segment_timeline())
    timing = report["metrics"]["timing_ms"]

    for key, value in timing.items():
        assert isinstance(value, float)
        assert value >= 0.0, key

    per_layer_sum = sum(v for k, v in timing.items() if k != "runner_total")
    assert timing["runner_total"] >= per_layer_sum


def test_segments_without_decision_report_why_in_chronological_order():
    report = _report_for(_three_segment_timeline())
    segments = report["metrics"]["segments"]

    assert len(segments) == 3
    assert segments[0]["has_decision"] is False
    assert segments[0]["no_decision_reason"] == "insufficient_conviction"
    assert segments[1]["has_decision"] is False
    assert segments[1]["no_decision_reason"] == "insufficient_conviction"
    for key in _SEGMENT_KEYS:
        assert key in segments[0]


def test_segment_with_decision_has_no_reason_and_positive_counts():
    report = _report_for(_three_segment_timeline())
    third = report["metrics"]["segments"][2]

    assert third["has_decision"] is True
    assert third["no_decision_reason"] is None
    assert third["decision_count"] == 1
    assert third["evaluation_count"] == 1
    assert third["hypothesis_count"] == 1


def test_segment_with_no_hypotheses_reports_no_hypotheses_reason():
    """Cluster sem nenhum evento de motion_state (so FrameProcessed) nao
    faz nenhum producer de Hypothesis disparar (motion_state fica UNKNOWN)
    - a razao registrada deve ser a mais cedo possivel na cadeia."""
    events = [_event(event_types.FRAME_PROCESSED, 0, 0.0), _event(event_types.TRACK_STARTED, 0, 0.0)]
    report = _report_for(events)

    assert report["metrics"]["counts"]["play_segments"] == 1
    segment = report["metrics"]["segments"][0]
    assert segment["has_decision"] is False
    assert segment["no_decision_reason"] == "no_hypotheses"


def test_summary_reflects_decision_rate_and_average_time():
    report = _report_for(_three_segment_timeline())
    summary = report["summary"]

    assert summary["total_segments"] == 3
    assert summary["segments_with_decision"] == 1
    assert summary["segments_without_decision"] == 2
    assert summary["decision_rate"] == 1 / 3
    assert summary["total_time_ms"] == report["metrics"]["timing_ms"]["runner_total"]
    assert summary["average_time_ms_per_segment"] == summary["total_time_ms"] / 3


def test_empty_event_timeline_produces_zero_segments_without_dividing_by_zero():
    report = _report_for([])

    assert report["metrics"]["counts"]["play_segments"] == 0
    assert report["metrics"]["segments"] == []
    assert report["summary"]["total_segments"] == 0
    assert report["summary"]["decision_rate"] == 0.0
    assert report["summary"]["average_time_ms_per_segment"] == 0.0


def test_determinism_same_input_produces_the_same_report_content():
    """segment_id e uuid4() novo a cada chamada (mesma ressalva de
    test_runner.py, W30) - determinismo aqui e sobre o CONTEUDO."""
    event_timeline = _three_segment_timeline()
    first = _report_for(event_timeline)
    second = _report_for(event_timeline)

    def _without_segment_id(report: dict) -> list[dict]:
        return [{k: v for k, v in segment.items() if k != "segment_id"} for segment in report["metrics"]["segments"]]

    assert _without_segment_id(first) == _without_segment_id(second)
    assert first["metrics"]["counts"] == second["metrics"]["counts"]

    non_timing_summary_keys = _SUMMARY_KEYS - {"total_time_ms", "average_time_ms_per_segment"}
    for key in non_timing_summary_keys:
        assert first["summary"][key] == second["summary"][key]
