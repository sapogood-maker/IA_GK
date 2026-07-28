"""Testes de worker.tools.validation_runner.run_validation (Fase 5A,
"Real World Validation Runner"). Reutiliza os fixtures reais ja
existentes em tests/conftest.py (real_video_path/corrupted_video_path/
missing_video_path) - o mesmo vídeo sintético mas real (10 frames,
64x48, 10fps, via OpenCV) usado por tests/inference/ desde a W5/W12."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker.tools.validation_runner import OUTPUT_FILENAMES, run_validation


async def test_missing_video_raises_and_still_logs(tmp_path: Path, missing_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"

    with pytest.raises(FileNotFoundError):
        await run_validation(missing_video_path, output_dir)

    assert output_dir.exists()  # diretorio de saida e criado mesmo em falha imediata
    log_content = (output_dir / "execution.log").read_text(encoding="utf-8")
    assert "validation_started" in log_content
    assert "não encontrado" in log_content.lower()
    # nada alem do log deveria existir - a execucao nunca chegou a processar nada
    assert not (output_dir / "execution_summary.json").exists()
    assert not (output_dir / "artifact.json").exists()


async def test_error_during_execution_is_logged_and_propagates(tmp_path: Path, corrupted_video_path: Path) -> None:
    """Video com extensao valida mas conteudo invalido - InferenceStage
    (reutilizada sem alteracao) deve falhar de verdade, sem mock."""
    output_dir = tmp_path / "validation_output"

    with pytest.raises(Exception):
        await run_validation(corrupted_video_path, output_dir)

    log_content = (output_dir / "execution.log").read_text(encoding="utf-8")
    assert "validation_started" in log_content
    assert "validation_aborted" in log_content or "ERROR" in log_content


async def test_output_directory_is_created_when_missing(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "nested" / "validation_output"
    assert not output_dir.exists()

    await run_validation(real_video_path, output_dir)

    assert output_dir.exists()


async def test_all_expected_files_are_generated(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"

    await run_validation(real_video_path, output_dir)

    for filename in OUTPUT_FILENAMES:
        assert (output_dir / filename).exists(), filename


async def test_execution_summary_has_the_expected_shape_and_real_values(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"

    summary = await run_validation(real_video_path, output_dir)

    assert set(summary.keys()) == {
        "video", "duration", "frames", "tracks", "play_segments", "decisions",
        "execution_time", "errors", "warnings",
    }
    assert summary["video"] == str(real_video_path)
    assert summary["frames"] == 10  # REAL_VIDEO_FRAME_COUNT (tests/conftest.py)
    assert isinstance(summary["duration"], float)
    assert isinstance(summary["tracks"], int)
    assert isinstance(summary["play_segments"], int)
    assert isinstance(summary["decisions"], int)
    assert summary["execution_time"] > 0.0
    assert summary["errors"] == []

    on_disk = json.loads((output_dir / "execution_summary.json").read_text(encoding="utf-8"))
    assert on_disk == summary


async def test_artifact_json_contains_the_cognitive_keys(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"

    await run_validation(real_video_path, output_dir)

    artifact = json.loads((output_dir / "artifact.json").read_text(encoding="utf-8"))
    assert "event_timeline" in artifact  # ja existia antes da Fase 5A (G2A)
    assert "cognitive_core_result" in artifact
    assert "cognitive_core_metrics" in artifact
    assert "cognitive_core_summary" in artifact
    assert "cognitive_quality" in artifact


async def test_quality_json_matches_the_cognitive_quality_embedded_in_the_artifact(
    tmp_path: Path, real_video_path: Path
) -> None:
    output_dir = tmp_path / "validation_output"

    await run_validation(real_video_path, output_dir)

    artifact = json.loads((output_dir / "artifact.json").read_text(encoding="utf-8"))
    quality = json.loads((output_dir / "quality.json").read_text(encoding="utf-8"))
    assert quality == artifact["cognitive_quality"]


async def test_error_analysis_and_recommendations_are_produced_without_ground_truth(
    tmp_path: Path, real_video_path: Path
) -> None:
    output_dir = tmp_path / "validation_output"

    summary = await run_validation(real_video_path, output_dir, ground_truth=None)

    error_analysis = json.loads((output_dir / "error_analysis.json").read_text(encoding="utf-8"))
    recommendations = json.loads((output_dir / "improvement_recommendations.json").read_text(encoding="utf-8"))
    assert "report" in error_analysis
    assert "improvement_candidates" in recommendations
    assert any("Ground Truth" in warning for warning in summary["warnings"])


async def test_execution_log_records_start_stages_and_finish(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"

    await run_validation(real_video_path, output_dir)

    log_content = (output_dir / "execution.log").read_text(encoding="utf-8")
    assert "validation_started" in log_content
    assert "stage_started name=InferenceStage" in log_content
    assert "stage_finished name=InferenceStage" in log_content
    assert "stage_started name=CognitiveCore" in log_content
    assert "stage_finished name=CognitiveCore" in log_content
    assert "validation_finished" in log_content
