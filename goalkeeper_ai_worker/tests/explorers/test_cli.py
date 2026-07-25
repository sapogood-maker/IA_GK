"""Testes de worker.explorers.cli - invoca run()/main() diretamente contra
um artifact.json temporario em disco (tmp_path), sem precisar de video/
YOLO/Redis."""
from __future__ import annotations

import json

import pytest

from worker.explorers.cli import build_parser, main, run

from .test_timeline_explorer import _consistent_artifact


@pytest.fixture
def artifact_path(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(_consistent_artifact()), encoding="utf-8")
    return path


def _run(artifact_path, *cli_args):
    parser = build_parser()
    args = parser.parse_args([str(artifact_path), *cli_args])
    return run(args)


def test_no_flags_returns_error_exit_code(artifact_path, capsys):
    exit_code = _run(artifact_path)
    assert exit_code == 1
    assert "Nenhuma opcao" in capsys.readouterr().err


def test_frame_prints_events_as_jsonl(artifact_path, capsys):
    exit_code = _run(artifact_path, "--frame", "0")
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)["frame_index"] == 0 for line in lines)


def test_time_range_filters_events(artifact_path, capsys):
    exit_code = _run(artifact_path, "--time-range", "0.1", "0.2")
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    frame_indexes = {json.loads(line)["frame_index"] for line in lines}
    assert frame_indexes == {1, 2}


def test_track_id_filters_events(artifact_path, capsys):
    exit_code = _run(artifact_path, "--track-id", "1")
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2


def test_event_type_filters_events(artifact_path, capsys):
    exit_code = _run(artifact_path, "--event-type", "FrameProcessed")
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3


def test_chronological_with_limit(artifact_path, capsys):
    exit_code = _run(artifact_path, "--chronological", "--limit", "2")
    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2


def test_explain_prints_readable_lines(artifact_path, capsys):
    exit_code = _run(artifact_path, "--explain", "0")
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "frame 0" in out


def test_compare_detections_prints_json_report(artifact_path, capsys):
    exit_code = _run(artifact_path, "--compare-detections")
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["consistent"] is True


def test_compare_tracking_prints_json_report(artifact_path, capsys):
    exit_code = _run(artifact_path, "--compare-tracking")
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["consistent"] is True


def test_compare_analysis_prints_json_report(artifact_path, capsys):
    exit_code = _run(artifact_path, "--compare-analysis")
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["consistent"] is True


def test_stats_prints_json_report(artifact_path, capsys):
    exit_code = _run(artifact_path, "--stats")
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["total_events"] == 13


def test_stats_with_export_writes_file(artifact_path, capsys, tmp_path):
    export_path = tmp_path / "exported_stats.json"
    exit_code = _run(artifact_path, "--stats", "--export", str(export_path))
    assert exit_code == 0
    written = json.loads(export_path.read_text(encoding="utf-8"))
    assert written["total_events"] == 13


def test_summary_prints_json_report(artifact_path, capsys):
    exit_code = _run(artifact_path, "--summary")
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["frame_count"] == 3


def test_main_reads_argv(monkeypatch, artifact_path, capsys):
    monkeypatch.setattr("sys.argv", ["cli.py", str(artifact_path), "--stats"])
    exit_code = main()
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["total_events"] == 13
