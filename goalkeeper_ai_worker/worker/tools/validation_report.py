"""validation_report: consolida os arquivos JÁ produzidos pelo Validation
Runner (Fase 5A) num único relatório de leitura fácil (Fase 6A,
"Validation Report").

NÃO recalcula absolutamente nada - só lê `artifact.json`,
`execution_summary.json`, `quality.json`, `error_analysis.json` e
`improvement_recommendations.json` de um diretório de saída já existente
e os reorganiza em `validation_report.json` (dict/list, os mesmos valores
já produzidos) e `validation_report.md` (texto legível, mesma informação,
formatada). Nunca executa o Cognitive Core, o Runner nem o Validation
Runner de novo.

`execution_summary.json` é o único arquivo OBRIGATÓRIO (sinaliza que a
validação ao menos começou e produziu algo) - os demais são
opcionais: uma validação cuja análise cognitiva falhou (Fase 5A, G2B,
falha isolada) legitimamente não produz `quality.json`/`error_analysis.json`/
`improvement_recommendations.json`, e este módulo reflete essa ausência
honestamente (`None`/"não disponível"), em vez de fabricar conteúdo ou
travar a geração do restante do relatório. Um JSON corrompido em
qualquer arquivo individual também não derruba o relatório inteiro - só
aquela seção fica indisponível."""
from __future__ import annotations

import json
from pathlib import Path

REQUIRED_FILENAME = "execution_summary.json"

_OPTIONAL_FILENAMES = {
    "artifact": "artifact.json",
    "quality": "quality.json",
    "error_analysis": "error_analysis.json",
    "improvement_recommendations": "improvement_recommendations.json",
}


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_validation_report(input_dir: str | Path) -> dict:
    """Lê os arquivos já produzidos em `input_dir` (o diretório gerado
    pelo Validation Runner, Fase 5A) e devolve o relatório consolidado -
    nenhum valor é recalculado, todos vêm diretamente dos arquivos."""
    input_dir = Path(input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Diretório de validação não encontrado: {input_dir}")

    execution_summary = _read_json(input_dir / REQUIRED_FILENAME)
    if execution_summary is None:
        raise FileNotFoundError(
            f"{REQUIRED_FILENAME} não encontrado (ou ilegível) em {input_dir} - "
            "nada para consolidar sem o resumo de execução do Validation Runner."
        )

    artifact = _read_json(input_dir / _OPTIONAL_FILENAMES["artifact"]) or {}
    quality = _read_json(input_dir / _OPTIONAL_FILENAMES["quality"])
    error_analysis = _read_json(input_dir / _OPTIONAL_FILENAMES["error_analysis"])
    improvement_recommendations = _read_json(input_dir / _OPTIONAL_FILENAMES["improvement_recommendations"])

    return {
        "video": {
            "path": execution_summary.get("video"),
            "status": artifact.get("status"),
            "frame_metadata": artifact.get("frame_metadata"),
        },
        "statistics": {
            "frames": execution_summary.get("frames"),
            "tracks": execution_summary.get("tracks"),
            "play_segments": execution_summary.get("play_segments"),
            "decisions": execution_summary.get("decisions"),
        },
        "quality": quality,
        "error_analysis": error_analysis,
        "improvement_recommendations": improvement_recommendations,
        "execution_errors": execution_summary.get("errors", []),
        "warnings": execution_summary.get("warnings", []),
        "execution_time": execution_summary.get("execution_time"),
    }


def _line(label: str, value) -> str:
    return f"{label}: {value if value is not None else 'não disponível'}"


def _section(title: str, lines: list[str]) -> str:
    separator = "=" * 49
    body = "\n".join(lines) if lines else "não disponível"
    return f"{separator}\n{title}\n{separator}\n{body}\n"


def _quality_lines(quality: dict | None) -> list[str]:
    if quality is None:
        return []
    lines: list[str] = []
    for key, value in quality.get("segment_counts", {}).items():
        lines.append(f"{key}: {value}")
    for key, value in quality.get("conversion_rates", {}).items():
        lines.append(f"{key}: {value:.2%}" if isinstance(value, float) else f"{key}: {value}")
    narrative = quality.get("summary", {}).get("narrative")
    if narrative:
        lines.append("")
        lines.append(narrative)
    return lines


def _error_analysis_lines(error_analysis: dict | None) -> list[str]:
    if error_analysis is None:
        return []
    report = error_analysis.get("report", {})
    lines = [
        f"error_count: {report.get('error_count')}",
        f"primary_error: {report.get('primary_error')}",
    ]
    for entry in report.get("ranking", []):
        lines.append(f"  - {entry['category']}: {entry['count']}")
    narrative = error_analysis.get("summary", {}).get("narrative")
    if narrative:
        lines.append("")
        lines.append(narrative)
    return lines


def _recommendations_lines(recommendations: dict | None) -> list[str]:
    if recommendations is None:
        return []
    lines: list[str] = []
    for candidate in recommendations.get("improvement_candidates", []):
        lines.append(
            f"{candidate['priority']}. {candidate['layer']} "
            f"(confidence={candidate['confidence']:.2f}) - {candidate['reason']}"
        )
    narrative = recommendations.get("summary", {}).get("narrative")
    if narrative:
        lines.append("")
        lines.append(narrative)
    return lines


def render_markdown(report: dict) -> str:
    """Renderiza o mesmo `report` (de `build_validation_report`) em texto
    legível - so formatacao, nenhum dado novo."""
    video = report["video"]
    statistics = report["statistics"]

    sections = [
        _section("VIDEO", [str(video.get("path") or "não disponível")]),
        _section(
            "EXECUÇÃO",
            [
                _line("Tempo", f"{report['execution_time']:.2f} s" if report.get("execution_time") is not None else None),
                _line("Frames", statistics.get("frames")),
                _line("Tracks", statistics.get("tracks")),
                _line("Play Segments", statistics.get("play_segments")),
                _line("Decisions", statistics.get("decisions")),
            ],
        ),
        _section("QUALITY", _quality_lines(report["quality"])),
        _section("ERROR ANALYSIS", _error_analysis_lines(report["error_analysis"])),
        _section("IMPROVEMENT RECOMMENDATIONS", _recommendations_lines(report["improvement_recommendations"])),
        _section("WARNINGS", report["warnings"] + report["execution_errors"]),
    ]
    return "\n".join(sections)


def write_validation_report(input_dir: str | Path, output_dir: str | Path | None = None) -> dict:
    """Constrói o relatório e grava `validation_report.json`/
    `validation_report.md` (default: dentro do próprio `input_dir`, junto
    dos arquivos que ele consolida). Devolve o dict do relatório."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir is not None else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_validation_report(input_dir)

    (output_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "validation_report.md").write_text(render_markdown(report), encoding="utf-8")

    return report
