"""Testes de worker.tools.batch_validation.run_batch_validation (Fase 5B,
"Batch Validation Runner"). Gera vídeos sintéticos reais (mesma receita de
tests/conftest.py::real_video_path, via OpenCV) diretamente num diretório
de lote - nao ha fixture pronta para "varios videos", entao a criacao e
local a este arquivo, sem alterar conftest.py."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from worker.tools.batch_validation import run_batch_validation

_FRAME_COUNT = 10
_FPS = 10.0
_WIDTH = 64
_HEIGHT = 48


def _write_real_video(path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(str(path), fourcc, _FPS, (_WIDTH, _HEIGHT))
    for i in range(_FRAME_COUNT):
        frame = np.full((_HEIGHT, _WIDTH, 3), i * 20 % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def _write_corrupted_video(path: Path) -> None:
    path.write_bytes(b"isto nao e um video de verdade")


async def test_missing_input_directory_raises_and_still_logs(tmp_path: Path) -> None:
    input_dir = tmp_path / "does-not-exist"
    output_dir = tmp_path / "validation_results"

    try:
        await run_batch_validation(input_dir, output_dir)
        assert False, "deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass

    assert output_dir.exists()
    log_content = (output_dir / "execution.log").read_text(encoding="utf-8")
    assert "batch_started" in log_content
    assert "não encontrado" in log_content.lower()


async def test_empty_input_directory_produces_zero_processed_videos(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    output_dir = tmp_path / "validation_results"

    stats = await run_batch_validation(input_dir, output_dir)

    assert stats["videos_processed"] == 0
    assert stats["successful"] == 0
    assert stats["failed"] == 0
    assert stats["total_errors"] == 0

    summary_csv = (output_dir / "summary.csv").read_text(encoding="utf-8")
    assert summary_csv.strip().splitlines() == ["video,duration,frames,tracks,play_segments,decisions,execution_time,errors,warnings"]


async def test_multiple_valid_videos_are_all_processed_into_individual_directories(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    _write_real_video(input_dir / "a.avi")
    _write_real_video(input_dir / "b.avi")
    _write_real_video(input_dir / "c.avi")
    output_dir = tmp_path / "validation_results"

    stats = await run_batch_validation(input_dir, output_dir)

    assert stats["videos_processed"] == 3
    assert stats["successful"] == 3
    assert stats["failed"] == 0

    for index in (1, 2, 3):
        video_dir = output_dir / f"video_{index:03d}"
        assert video_dir.exists()
        assert (video_dir / "execution_summary.json").exists()
        assert (video_dir / "artifact.json").exists()


async def test_invalid_video_is_recorded_as_an_error_without_stopping_the_batch(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    _write_real_video(input_dir / "a.avi")
    _write_corrupted_video(input_dir / "b.avi")
    _write_real_video(input_dir / "c.avi")
    output_dir = tmp_path / "validation_results"

    stats = await run_batch_validation(input_dir, output_dir)

    assert stats["videos_processed"] == 3
    assert stats["successful"] == 2
    assert stats["failed"] == 1
    assert stats["total_errors"] >= 1

    # video_002 (o corrompido, ordem alfabetica a/b/c) tem seu proprio
    # diretorio e log de falha - o lote nao para.
    assert (output_dir / "video_001").exists()
    assert (output_dir / "video_002").exists()
    assert (output_dir / "video_003").exists()
    assert (output_dir / "video_003" / "execution_summary.json").exists()


async def test_summary_csv_has_one_row_per_video_with_the_expected_columns(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    _write_real_video(input_dir / "a.avi")
    _write_corrupted_video(input_dir / "b.avi")
    output_dir = tmp_path / "validation_results"

    await run_batch_validation(input_dir, output_dir)

    with (output_dir / "summary.csv").open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 2
    assert set(rows[0].keys()) == {
        "video", "duration", "frames", "tracks", "play_segments", "decisions",
        "execution_time", "errors", "warnings",
    }
    assert rows[0]["errors"] == ""  # video valido, sem erro
    assert rows[1]["errors"] != ""  # video corrompido, erro registrado


async def test_summary_json_has_the_expected_statistics(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    _write_real_video(input_dir / "a.avi")
    _write_real_video(input_dir / "b.avi")
    output_dir = tmp_path / "validation_results"

    stats = await run_batch_validation(input_dir, output_dir)

    assert set(stats.keys()) == {
        "videos_processed", "successful", "failed", "average_execution_time",
        "average_tracks", "average_segments", "average_decisions", "total_errors",
    }
    on_disk = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert on_disk == stats
    assert stats["average_execution_time"] > 0.0


async def test_batch_log_records_start_each_video_and_finish(tmp_path: Path) -> None:
    input_dir = tmp_path / "videos"
    input_dir.mkdir()
    _write_real_video(input_dir / "a.avi")
    output_dir = tmp_path / "validation_results"

    await run_batch_validation(input_dir, output_dir)

    log_content = (output_dir / "execution.log").read_text(encoding="utf-8")
    assert "batch_started" in log_content
    assert "videos_found count=1" in log_content
    assert "video_started index=1" in log_content
    assert "video_finished index=1" in log_content
    assert "batch_finished" in log_content
