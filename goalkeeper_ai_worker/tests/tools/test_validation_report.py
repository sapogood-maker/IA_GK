"""Testes de worker.tools.validation_report (Fase 6A, "Validation
Report"). Usa saidas REAIS do Validation Runner (Fase 5A, run_validation
ja existente) como fixture - nunca fabrica o conteudo dos arquivos que
este modulo consolida, ja que ele proprio nao recalcula nada."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker.tools.validation_report import build_validation_report, render_markdown, write_validation_report
from worker.tools.validation_runner import run_validation


@pytest.fixture
async def validation_output(tmp_path: Path, real_video_path: Path) -> Path:
    output_dir = tmp_path / "validation_output"
    await run_validation(real_video_path, output_dir)
    return output_dir


def test_missing_input_directory_raises() -> None:
    with pytest.raises(FileNotFoundError):
        build_validation_report(Path("this/does/not/exist"))


async def test_missing_execution_summary_raises(tmp_path: Path) -> None:
    input_dir = tmp_path / "empty_dir"
    input_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        build_validation_report(input_dir)


async def test_missing_optional_file_is_reported_as_unavailable_not_a_crash(validation_output: Path) -> None:
    (validation_output / "quality.json").unlink()

    report = build_validation_report(validation_output)

    assert report["quality"] is None
    # o restante do relatorio continua disponivel normalmente
    assert report["video"]["path"] is not None
    assert report["error_analysis"] is not None


async def test_invalid_json_in_one_file_does_not_break_the_whole_report(validation_output: Path) -> None:
    (validation_output / "error_analysis.json").write_text("{isto nao e json valido", encoding="utf-8")

    report = build_validation_report(validation_output)

    assert report["error_analysis"] is None
    assert report["quality"] is not None  # as demais secoes continuam intactas


async def test_full_report_reflects_the_files_verbatim_without_recomputation(validation_output: Path) -> None:
    artifact = json.loads((validation_output / "artifact.json").read_text(encoding="utf-8"))
    execution_summary = json.loads((validation_output / "execution_summary.json").read_text(encoding="utf-8"))
    quality = json.loads((validation_output / "quality.json").read_text(encoding="utf-8"))
    error_analysis = json.loads((validation_output / "error_analysis.json").read_text(encoding="utf-8"))
    recommendations = json.loads(
        (validation_output / "improvement_recommendations.json").read_text(encoding="utf-8")
    )

    report = build_validation_report(validation_output)

    assert report["video"]["path"] == execution_summary["video"]
    assert report["video"]["status"] == artifact["status"]
    assert report["video"]["frame_metadata"] == artifact["frame_metadata"]
    assert report["statistics"] == {
        "frames": execution_summary["frames"],
        "tracks": execution_summary["tracks"],
        "play_segments": execution_summary["play_segments"],
        "decisions": execution_summary["decisions"],
    }
    assert report["quality"] == quality
    assert report["error_analysis"] == error_analysis
    assert report["improvement_recommendations"] == recommendations
    assert report["execution_errors"] == execution_summary["errors"]
    assert report["warnings"] == execution_summary["warnings"]
    assert report["execution_time"] == execution_summary["execution_time"]


async def test_empty_report_with_only_execution_summary_present(tmp_path: Path, real_video_path: Path) -> None:
    output_dir = tmp_path / "validation_output"
    await run_validation(real_video_path, output_dir)
    for filename in ("artifact.json", "quality.json", "error_analysis.json", "improvement_recommendations.json"):
        (output_dir / filename).unlink()

    report = build_validation_report(output_dir)

    assert report["video"]["status"] is None
    assert report["video"]["frame_metadata"] is None
    assert report["quality"] is None
    assert report["error_analysis"] is None
    assert report["improvement_recommendations"] is None
    assert report["video"]["path"] is not None  # ainda vem do execution_summary.json

    # nao deve travar a geracao do markdown mesmo com quase tudo ausente
    markdown = render_markdown(report)
    assert "não disponível" in markdown


async def test_markdown_has_all_expected_sections_in_order(validation_output: Path) -> None:
    report = build_validation_report(validation_output)

    markdown = render_markdown(report)

    sections = ["VIDEO", "EXECUÇÃO", "QUALITY", "ERROR ANALYSIS", "IMPROVEMENT RECOMMENDATIONS", "WARNINGS"]
    positions = [markdown.index(section) for section in sections]
    assert positions == sorted(positions)  # aparecem na ordem esperada
    assert report["video"]["path"] in markdown
    assert f"{report['execution_time']:.2f} s" in markdown


async def test_write_validation_report_creates_both_output_files(validation_output: Path) -> None:
    report = write_validation_report(validation_output)

    json_path = validation_output / "validation_report.json"
    md_path = validation_output / "validation_report.md"
    assert json_path.exists()
    assert md_path.exists()

    on_disk = json.loads(json_path.read_text(encoding="utf-8"))
    assert on_disk == report
    assert "VIDEO" in md_path.read_text(encoding="utf-8")
