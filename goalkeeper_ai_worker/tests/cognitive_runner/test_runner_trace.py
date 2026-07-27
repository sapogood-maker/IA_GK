"""Testes de worker.cognitive_runner.runner.run_cognitive_core_with_trace
(Phase 2, G2D) - o Execution Trace elimina a segunda execucao completa do
Cognitive Core que build_cognitive_report() fazia na G2C. Fixtures
deliberadamente equivalentes as de tests/cognitive_runner/test_runner.py."""
from __future__ import annotations

from uuid import uuid4

from worker.cognitive_runner.runner import run_cognitive_core, run_cognitive_core_with_trace
from worker.conviction.conviction_level import ConvictionLevel
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
        _event(event_types.TRACK_STARTED, base_frame, start_timestamp),
        _event(event_types.OBJECT_STOPPED, base_frame + 1, start_timestamp + 0.05, metadata={"motion_state": "stopped"}),
        _event(event_types.TRACK_UPDATED, base_frame + 2, start_timestamp + 0.1),
    ]


def _three_segment_timeline() -> list[dict]:
    events: list[dict] = []
    for cluster_index, start_timestamp in enumerate((0.0, 10.0, 20.0)):
        events.extend(_cluster(base_frame=cluster_index * 100, start_timestamp=start_timestamp))
    return events


_SEGMENT_ENTRY_KEYS = {
    "segment", "segment_events", "memory", "working_state", "hypotheses", "conviction_set",
    "planning_set", "decision_set", "evaluation_set", "timing_ms",
}
_SEGMENT_TIMING_KEYS = {
    "memory", "working_state", "hypothesis", "conviction", "planning", "decision", "evaluation",
}


def test_results_component_matches_bare_run_cognitive_core():
    """`run_cognitive_core_with_trace()[0]` deve ser o MESMO conteudo que
    `run_cognitive_core()` sempre produziu - o contrato publico do Runner
    nao mudou (so segment_id, uuid4() novo a cada chamada, difere)."""
    event_timeline = _three_segment_timeline()
    bare_results = run_cognitive_core(event_timeline)
    traced_results, _ = run_cognitive_core_with_trace(event_timeline)

    def _without_segment_id(results: list[dict]) -> list[dict]:
        return [{k: v for k, v in result.items() if k != "segment_id"} for result in results]

    assert _without_segment_id(bare_results) == _without_segment_id(traced_results)


def test_trace_has_expected_top_level_and_per_segment_shape():
    _, trace = run_cognitive_core_with_trace(_three_segment_timeline())

    assert set(trace.keys()) == {"raw_events", "derived_events", "segments", "timing_ms"}
    assert isinstance(trace["raw_events"], list)
    assert isinstance(trace["derived_events"], list)
    assert len(trace["segments"]) == 3
    assert set(trace["timing_ms"].keys()) == {"timeline", "segmentation", "enrichment", "execute_total"}

    for entry in trace["segments"]:
        assert set(entry.keys()) == _SEGMENT_ENTRY_KEYS
        assert set(entry["timing_ms"].keys()) == _SEGMENT_TIMING_KEYS


def test_trace_timings_are_non_negative_and_execute_total_is_largest():
    _, trace = run_cognitive_core_with_trace(_three_segment_timeline())

    for key, value in trace["timing_ms"].items():
        assert isinstance(value, float)
        assert value >= 0.0, key

    non_execute_total = trace["timing_ms"]["timeline"] + trace["timing_ms"]["segmentation"] + trace["timing_ms"]["enrichment"]
    per_segment_total = sum(
        sum(entry["timing_ms"].values()) for entry in trace["segments"]
    )
    assert trace["timing_ms"]["execute_total"] >= non_execute_total + per_segment_total


def test_trace_conviction_set_is_threaded_across_segments():
    """Mesma prova de encadeamento da G2A (test_runner.py), agora lida
    diretamente do objeto ConvictionSet retido no trace: o nivel so cruza
    para STABLE no 3o segmento (limiar de 3 observacoes consecutivas)."""
    _, trace = run_cognitive_core_with_trace(_three_segment_timeline())

    levels = [
        entry["conviction_set"].track_convictions["stationary:track:1"].level for entry in trace["segments"]
    ]
    assert levels == [ConvictionLevel.EMERGING, ConvictionLevel.EMERGING, ConvictionLevel.STABLE]


def test_trace_segment_events_match_the_results_segment_boundaries():
    results, trace = run_cognitive_core_with_trace(_three_segment_timeline())

    for result, entry in zip(results, trace["segments"]):
        assert entry["segment"].segment_id == result["segment_id"]
        assert all(
            entry["segment"].start_frame <= event["frame_index"] <= entry["segment"].end_frame
            for event in entry["segment_events"]
        )
