"""Testes de worker.explorers.timeline_explorer.TimelineExplorer.

Todos usam um artifact sintetico (dict a mao) - TimelineExplorer e uma
API de consulta pura, testavel sem video/YOLO/Redis, mesmo estilo de
tests/timeline/test_builder.py."""
from __future__ import annotations

import json

from worker.explorers.timeline_explorer import TimelineExplorer


def _event(
    event_type: str,
    frame_index: int,
    event_id: str,
    timestamp_seconds: float | None = None,
    track_id: int | None = None,
    entity: str | None = None,
    confidence: float | None = None,
    metadata: dict | None = None,
    parent_event_id: str | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp_seconds,
        "track_id": track_id,
        "entity": entity,
        "confidence": confidence,
        "position": None,
        "metadata": metadata or {},
        "parent_event_id": parent_event_id,
    }


def _consistent_artifact() -> dict:
    """3 frames, deteccoes/tracking/analyzers todos coerentes entre si -
    caso "tudo bate" para as tres comparacoes."""
    timeline = [
        _event("FrameProcessed", 0, "e1", timestamp_seconds=0.0),
        _event("ObjectDetected", 0, "e2", timestamp_seconds=0.0, entity="person", confidence=0.9),
        _event("TrackStarted", 0, "e3", timestamp_seconds=0.0, track_id=1, entity="person"),
        _event("FrameProcessed", 1, "e4", timestamp_seconds=0.1),
        _event("TrackUpdated", 1, "e5", timestamp_seconds=0.1, track_id=1, entity="person"),
        _event("FrameProcessed", 2, "e6", timestamp_seconds=0.2),
        _event("ObjectDetected", 2, "e7", timestamp_seconds=0.2, entity="ball", confidence=0.6),
        _event(
            "AnalyzerStarted", 2, "e8", timestamp_seconds=0.19,
            metadata={"analyzer_name": "goal_geometry", "analyzer_version": "1.0.0"},
        ),
        _event(
            "AnalyzerFinished", 2, "af-goal-geo", timestamp_seconds=0.2,
            metadata={"analyzer_name": "goal_geometry", "analyzer_version": "1.0.0"},
        ),
        _event(
            "AnalyzerStarted", 2, "e10", timestamp_seconds=0.19,
            metadata={"analyzer_name": "goalkeeper_decision_evaluation", "analyzer_version": "1.0.0"},
        ),
        _event(
            "AnalyzerFinished", 2, "af-gde", timestamp_seconds=0.2,
            metadata={"analyzer_name": "goalkeeper_decision_evaluation", "analyzer_version": "1.0.0"},
        ),
        _event(
            "RuleEvaluated", 2, "e12", timestamp_seconds=0.2,
            metadata={"analyzer_name": "goalkeeper_decision_evaluation", "rule_name": "rule_a", "passed": True},
            parent_event_id="af-gde",
        ),
        _event(
            "RuleEvaluated", 2, "e13", timestamp_seconds=0.2,
            metadata={"analyzer_name": "goalkeeper_decision_evaluation", "rule_name": "rule_b", "passed": False},
            parent_event_id="af-gde",
        ),
    ]
    return {
        "frame_metadata": {"frame_count": 3, "width": 100, "height": 100, "fps": 10.0, "duration_seconds": 0.3},
        "detection_results": [
            {"frame_index": 0, "detections": [{"label": "person"}]},
            {"frame_index": 1, "detections": []},
            {"frame_index": 2, "detections": [{"label": "sports ball"}]},
        ],
        "tracking_statistics": {"total_tracks": 1, "lost_tracks": 0},
        "scene_statistics": {"events_by_type": {"track_started": 1, "track_updated": 1}},
        "analysis_statistics": {"analyzers_run": ["goal_geometry", "goalkeeper_decision_evaluation"]},
        "analysis_results": {
            "goal_geometry": {"frame_index": 2, "analyzer_name": "goal_geometry"},
            "goalkeeper_decision_evaluation": {
                "frame_index": 2,
                "analyzer_name": "goalkeeper_decision_evaluation",
                "rules_evaluated": ["rule_a", "rule_b"],
            },
        },
        "event_timeline": timeline,
    }


# --- Navegacao ---

def test_by_frame_returns_only_that_frames_events():
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.by_frame(0)
    assert {e["event_id"] for e in events} == {"e1", "e2", "e3"}


def test_by_time_range_is_inclusive_on_both_ends():
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.by_time_range(0.1, 0.2)
    frame_indexes = {e["frame_index"] for e in events}
    assert frame_indexes == {1, 2}


def test_by_frame_range_is_inclusive_on_both_ends():
    """Sprint W30: usado pelo PlaySegmenter para extrair os eventos de
    cada segmento por indice de frame, mesma familia de by_time_range."""
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.by_frame_range(1, 2)
    assert {e["frame_index"] for e in events} == {1, 2}


def test_by_frame_range_returns_empty_list_outside_range():
    explorer = TimelineExplorer(_consistent_artifact())
    assert explorer.by_frame_range(50, 60) == []


def test_by_track_id_returns_only_events_of_that_track():
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.by_track_id(1)
    assert {e["event_id"] for e in events} == {"e3", "e5"}


def test_by_event_type_filters_correctly():
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.by_event_type("FrameProcessed")
    assert len(events) == 3


def test_chronological_is_sorted_by_frame_index_even_if_input_is_shuffled():
    artifact = _consistent_artifact()
    artifact["event_timeline"] = list(reversed(artifact["event_timeline"]))
    explorer = TimelineExplorer(artifact)
    frame_indexes = [e["frame_index"] for e in explorer.chronological()]
    assert frame_indexes == sorted(frame_indexes)


def test_reconstruct_without_cutoff_returns_everything():
    explorer = TimelineExplorer(_consistent_artifact())
    assert len(explorer.reconstruct()) == 13


def test_reconstruct_with_cutoff_stops_at_that_frame():
    explorer = TimelineExplorer(_consistent_artifact())
    events = explorer.reconstruct(up_to_frame=0)
    assert all(e["frame_index"] <= 0 for e in events)
    assert len(events) == 3


# --- Explain ---

def test_explain_produces_one_readable_line_per_event():
    explorer = TimelineExplorer(_consistent_artifact())
    lines = explorer.explain(0)
    assert len(lines) == 3
    assert "frame 0" in lines[0]
    assert "person" in lines[1]  # ObjectDetected com entity=person
    assert "track_id=1" in lines[2]  # TrackStarted


def test_explain_includes_rule_outcome():
    explorer = TimelineExplorer(_consistent_artifact())
    lines = explorer.explain(2)
    rule_lines = [line for line in lines if "rule_a" in line]
    assert rule_lines
    assert "passou" in rule_lines[0]


# --- Comparacoes: caso consistente ---

def test_compare_with_detections_all_consistent():
    explorer = TimelineExplorer(_consistent_artifact())
    result = explorer.compare_with_detections()
    assert result["consistent"] is True
    assert result["frames_checked"] == 3
    assert result["frames_matching"] == 3
    assert result["mismatches"] == []


def test_compare_with_tracking_all_consistent():
    explorer = TimelineExplorer(_consistent_artifact())
    result = explorer.compare_with_tracking()
    assert result["consistent"] is True
    assert result["mismatches"] == []


def test_compare_with_analysis_all_consistent():
    explorer = TimelineExplorer(_consistent_artifact())
    result = explorer.compare_with_analysis()
    assert result["consistent"] is True
    assert result["missing_from_timeline"] == []
    assert result["unexpected_in_timeline"] == []
    assert result["rule_consistency"]["goalkeeper_decision_evaluation"]["consistent"] is True


# --- Comparacoes: mismatch proposital ---

def test_compare_with_detections_reports_mismatch():
    artifact = _consistent_artifact()
    # Injeta um ObjectDetected extra no frame 1, onde detection_results diz 0.
    artifact["event_timeline"].append(_event("ObjectDetected", 1, "extra", entity="ghost"))
    explorer = TimelineExplorer(artifact)

    result = explorer.compare_with_detections()

    assert result["consistent"] is False
    assert result["mismatches"] == [{"frame_index": 1, "timeline_count": 1, "detection_results_count": 0}]


def test_compare_with_tracking_reports_mismatch():
    artifact = _consistent_artifact()
    artifact["scene_statistics"]["events_by_type"]["track_lost"] = 1  # Timeline nao tem nenhum TrackLost
    explorer = TimelineExplorer(artifact)

    result = explorer.compare_with_tracking()

    assert result["consistent"] is False
    assert {"event_type": "TrackLost", "scene_statistics_count": 1, "timeline_count": 0} in result["mismatches"]


def test_compare_with_analysis_reports_missing_analyzer():
    artifact = _consistent_artifact()
    artifact["analysis_statistics"]["analyzers_run"].append("ball_position")  # nunca rodou na Timeline
    explorer = TimelineExplorer(artifact)

    result = explorer.compare_with_analysis()

    assert result["consistent"] is False
    assert result["missing_from_timeline"] == ["ball_position"]


def test_compare_with_analysis_reports_rule_inconsistency():
    artifact = _consistent_artifact()
    artifact["analysis_results"]["goalkeeper_decision_evaluation"]["rules_evaluated"].append("rule_c")
    explorer = TimelineExplorer(artifact)

    result = explorer.compare_with_analysis()

    assert result["consistent"] is False
    rule_check = result["rule_consistency"]["goalkeeper_decision_evaluation"]
    assert rule_check["consistent"] is False
    assert "rule_c" in rule_check["expected_rules"]
    assert "rule_c" not in rule_check["timeline_rules"]


# --- Estatisticas ---

def test_statistics_counts_totals_and_ranges():
    explorer = TimelineExplorer(_consistent_artifact())
    stats = explorer.statistics()

    assert stats["total_events"] == 13
    assert stats["by_event_type"]["FrameProcessed"] == 3
    assert stats["by_track_id"] == {1: 2}
    assert stats["frame_range"] == [0, 2]
    assert stats["time_range_seconds"] == [0.0, 0.2]


def test_summary_aggregates_artifact_level_facts():
    explorer = TimelineExplorer(_consistent_artifact())
    summary = explorer.summary()

    assert summary["frame_count"] == 3
    assert summary["total_tracks"] == 1
    assert summary["total_events"] == 13
    assert summary["rules_evaluated"] == 2
    assert summary["rules_passed"] == 1
    assert summary["rules_failed"] == 1
    assert set(summary["analyzers_run"]) == {"goal_geometry", "goalkeeper_decision_evaluation"}


def test_export_statistics_writes_valid_json(tmp_path):
    explorer = TimelineExplorer(_consistent_artifact())
    output_path = tmp_path / "stats.json"

    explorer.export_statistics(output_path)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["total_events"] == 13


def test_from_file_loads_artifact_from_disk(tmp_path):
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(json.dumps(_consistent_artifact()), encoding="utf-8")

    explorer = TimelineExplorer.from_file(artifact_path)

    assert len(explorer.chronological()) == 13
