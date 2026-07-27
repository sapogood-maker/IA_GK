"""Testes de worker.cognitive_runner.analyzer.analyze_cognitive_quality
(Fase 3, "Cognitive Quality") - indicadores de qualidade do raciocinio.
Nao mocka nenhuma camada do Cognitive Core - roda a cadeia real via
run_cognitive_core_with_trace() (mesma fonte de dados de report.py),
fixtures deliberadamente equivalentes as de tests/cognitive_runner/
test_report.py."""
from __future__ import annotations

from uuid import uuid4

import pytest

from worker.cognitive_runner.analyzer import analyze_cognitive_quality
from worker.cognitive_runner.runner import run_cognitive_core_with_trace
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
    """3 clusters do mesmo track_id=1 parado, separados por ~10s - o 3o
    segmento cruza o limiar STABLE (3 observacoes consecutivas) e produz
    decisao; os 2 primeiros nao."""
    events: list[dict] = []
    for cluster_index, start_timestamp in enumerate((0.0, 10.0, 20.0)):
        events.extend(_cluster(base_frame=cluster_index * 100, start_timestamp=start_timestamp))
    return events


def _quality_for(event_timeline: list[dict]) -> dict:
    _, trace = run_cognitive_core_with_trace(event_timeline)
    return analyze_cognitive_quality(trace)


def test_report_shape_is_plain_dict_list_with_no_new_dataclasses():
    quality = _quality_for(_three_segment_timeline())

    assert set(quality.keys()) == {
        "segment_counts", "conversion_rates", "conviction_persistence", "temporal_analysis", "summary",
    }
    for value in quality.values():
        assert isinstance(value, dict)


def test_segment_counts_are_correct_for_three_segments():
    quality = _quality_for(_three_segment_timeline())
    counts = quality["segment_counts"]

    assert counts == {
        "segments_analyzed": 3,
        "segments_with_hypothesis": 3,
        "segments_without_hypothesis": 0,
        "segments_with_stable_conviction": 1,
        "segments_with_decision": 1,
        "segments_without_decision": 2,
    }


def test_conversion_rates_reflect_the_real_funnel():
    quality = _quality_for(_three_segment_timeline())
    rates = quality["conversion_rates"]

    assert rates["hypothesis_to_conviction"] == pytest.approx(1 / 3)
    assert rates["conviction_to_planning"] == pytest.approx(1.0)
    assert rates["planning_to_decision"] == pytest.approx(1.0)
    assert rates["decision_to_evaluation"] == pytest.approx(1.0)


def test_conviction_persistence_reads_real_core_fields():
    quality = _quality_for(_three_segment_timeline())
    persistence = quality["conviction_persistence"]

    # a unica conviction do fixture so atinge STABLE no 3o segmento
    # (t=20.1s), tendo sido observada pela 1a vez em t=0.1s (segmento 0).
    assert persistence["average_time_to_stable_seconds"] == pytest.approx(20.0)
    assert persistence["longest_growth_streak"] == 3  # consecutive_observations no 3o segmento
    assert persistence["convictions_dropped"] == 0  # a mesma conviction persiste os 3 segmentos
    assert persistence["convictions_promoted"] == 1  # 1 unica transicao STRENGTHENED (EMERGING -> STABLE)


def test_temporal_analysis_uses_real_timestamps_and_play_segment_fields():
    event_timeline = _three_segment_timeline()
    _, trace = run_cognitive_core_with_trace(event_timeline)
    quality = analyze_cognitive_quality(trace)
    temporal = quality["temporal_analysis"]

    timestamps = sorted(event["timestamp_seconds"] for event in trace["raw_events"])
    expected_average_delta = sum(b - a for a, b in zip(timestamps, timestamps[1:])) / (len(timestamps) - 1)
    assert temporal["average_time_between_events_seconds"] == pytest.approx(expected_average_delta)

    assert temporal["average_segment_duration_seconds"] > 0.0
    assert temporal["segment_size_distribution"]["sizes"] == [4, 4, 4]  # so eventos RAW por PlaySegment (W30)
    assert temporal["segment_size_distribution"]["min_events"] == 4
    assert temporal["segment_size_distribution"]["max_events"] == 4
    assert temporal["segment_size_distribution"]["mean_events"] == 4.0


def test_primary_bottleneck_and_textual_summary_for_mostly_stuck_video():
    quality = _quality_for(_three_segment_timeline())
    summary = quality["summary"]

    assert summary["bottleneck_distribution"] == {"insufficient_conviction": 2}
    assert summary["primary_bottleneck"] == "insufficient_conviction"
    assert summary["narrative"].startswith("A maioria")
    assert "Conviction" in summary["narrative"]
    assert "STABLE" in summary["narrative"]


def test_empty_event_timeline_produces_zero_segments_without_crashing():
    quality = _quality_for([])

    assert quality["segment_counts"] == {
        "segments_analyzed": 0,
        "segments_with_hypothesis": 0,
        "segments_without_hypothesis": 0,
        "segments_with_stable_conviction": 0,
        "segments_with_decision": 0,
        "segments_without_decision": 0,
    }
    assert quality["conversion_rates"] == {
        "hypothesis_to_conviction": 0.0,
        "conviction_to_planning": 0.0,
        "planning_to_decision": 0.0,
        "decision_to_evaluation": 0.0,
    }
    assert quality["conviction_persistence"]["average_time_to_stable_seconds"] is None
    assert quality["conviction_persistence"]["longest_growth_streak"] == 0
    assert quality["temporal_analysis"]["average_time_between_events_seconds"] is None
    assert quality["temporal_analysis"]["average_segment_duration_seconds"] is None
    assert quality["temporal_analysis"]["segment_size_distribution"]["sizes"] == []
    assert quality["summary"]["bottleneck_distribution"] == {}
    assert quality["summary"]["primary_bottleneck"] is None
    assert quality["summary"]["narrative"] == "Nenhum segmento foi analisado."


def test_video_without_any_hypothesis_reports_no_hypotheses_bottleneck():
    """Cluster sem nenhum evento de motion_state (so FrameProcessed +
    TrackStarted) nao faz nenhum producer de Hypothesis disparar."""
    events = [_event(event_types.FRAME_PROCESSED, 0, 0.0), _event(event_types.TRACK_STARTED, 0, 0.0)]
    quality = _quality_for(events)

    assert quality["segment_counts"]["segments_analyzed"] == 1
    assert quality["segment_counts"]["segments_with_hypothesis"] == 0
    assert quality["segment_counts"]["segments_without_hypothesis"] == 1
    assert quality["conversion_rates"]["hypothesis_to_conviction"] == 0.0
    assert quality["summary"]["bottleneck_distribution"] == {"no_hypotheses": 1}
    assert quality["summary"]["primary_bottleneck"] == "no_hypotheses"
    assert "Hypothesis" in quality["summary"]["narrative"]


def test_video_that_produces_a_decision_reports_it_in_segment_counts_and_narrative():
    quality = _quality_for(_three_segment_timeline())

    assert quality["segment_counts"]["segments_with_decision"] == 1
    # nem todas as jogadas produziram decisao neste fixture - narrativa nao
    # deve alegar 100%.
    assert "Todas as jogadas" not in quality["summary"]["narrative"]


def test_single_segment_video_never_has_a_decision_yet_still_gets_a_narrative():
    """O 1o PlaySegment de QUALQUER video parte de um ConvictionSet vazio
    (ConvictionSet() no inicio de _execute()) - o limiar STABLE exige 3
    observacoes consecutivas, entao nenhum video pode produzir uma decisao
    logo no 1o segmento. Por isso a narrativa "Todas as jogadas..." e
    estruturalmente inalcancavel para qualquer entrada real - achado desta
    sprint, documentado aqui em vez de testado como caminho feliz."""
    events = [
        _event(event_types.TRACK_STARTED, 0, 0.0),
        _event(event_types.OBJECT_STOPPED, 1, 0.05, metadata={"motion_state": "stopped"}),
        _event(event_types.TRACK_UPDATED, 2, 0.1),
    ]
    quality = _quality_for(events)

    assert quality["segment_counts"]["segments_with_decision"] == 0
    assert quality["summary"]["primary_bottleneck"] == "insufficient_conviction"
    assert quality["summary"]["narrative"] != "Nenhum segmento foi analisado."
    assert "Todas as jogadas" not in quality["summary"]["narrative"]
