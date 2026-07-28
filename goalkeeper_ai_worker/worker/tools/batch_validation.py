"""batch_validation: roda worker.tools.validation_runner.run_validation()
(Fase 5A) para cada vídeo de um diretório, produzindo um relatório
consolidado (Fase 5B, "Batch Validation Runner").

NAO implementa nenhuma lógica própria de validação - só descobre arquivos
de vídeo num diretório e chama `run_validation()` para cada um,
INTEGRALMENTE, sem alterar uma linha dele. Qualquer melhoria futura em
`run_validation()` beneficia automaticamente esta ferramenta, já que ela
é CHAMADA, nunca duplicada.

Falha em UM vídeo (corrompido, etc.) NÃO interrompe o lote - registrada e
o processamento continua para os demais (mesma filosofia de isolamento de
falha já estabelecida em `CognitiveRunnerStage` (G2B) e no próprio
Validation Runner (Fase 5A))."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import time
from pathlib import Path

from worker.tools.validation_runner import run_validation

logger = logging.getLogger("worker.tools.batch_validation")

# Descoberta de arquivos por extensao - heuristica desta ferramenta, nao
# validacao real (a validade de fato e decidida pelo VideoReader real,
# via run_validation - um arquivo com extensao de video mas conteudo
# invalido simplesmente falha e e registrado, nunca filtrado aqui).
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")

SUMMARY_CSV_FIELDS = (
    "video", "duration", "frames", "tracks", "play_segments", "decisions",
    "execution_time", "errors", "warnings",
)


def _attach_file_logger(output_dir: Path) -> logging.Handler:
    handler = logging.FileHandler(output_dir / "execution.log", mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return handler


def _discover_videos(input_dir: Path) -> list[Path]:
    return sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def _failure_summary(video_path: Path, error: Exception, execution_time: float) -> dict:
    return {
        "video": str(video_path),
        "duration": None,
        "frames": None,
        "tracks": None,
        "play_segments": None,
        "decisions": None,
        "execution_time": execution_time,
        "errors": [str(error)],
        "warnings": [],
    }


def _row_for_csv(summary: dict) -> dict:
    return {
        "video": summary.get("video"),
        "duration": summary.get("duration"),
        "frames": summary.get("frames"),
        "tracks": summary.get("tracks"),
        "play_segments": summary.get("play_segments"),
        "decisions": summary.get("decisions"),
        "execution_time": summary.get("execution_time"),
        "errors": "; ".join(summary.get("errors") or []),
        "warnings": "; ".join(summary.get("warnings") or []),
    }


def _write_summary_csv(path: Path, summaries: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SUMMARY_CSV_FIELDS)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(_row_for_csv(summary))


def _mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _write_summary_json(path: Path, summaries: list[dict], successful: int, failed: int) -> dict:
    stats = {
        "videos_processed": len(summaries),
        "successful": successful,
        "failed": failed,
        "average_execution_time": _mean(
            [s["execution_time"] for s in summaries if s.get("execution_time") is not None]
        ),
        "average_tracks": _mean([s["tracks"] for s in summaries if s.get("tracks") is not None]),
        "average_segments": _mean([s["play_segments"] for s in summaries if s.get("play_segments") is not None]),
        "average_decisions": _mean([s["decisions"] for s in summaries if s.get("decisions") is not None]),
        "total_errors": sum(len(s.get("errors") or []) for s in summaries),
    }
    path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


async def run_batch_validation(
    input_dir: str | Path, output_dir: str | Path, ground_truth: list[dict] | None = None
) -> dict:
    """Roda `run_validation()` (Fase 5A, reutilizada sem alteração) para
    cada vídeo encontrado em `input_dir`, gravando um diretório individual
    `video_NNN/` por vídeo dentro de `output_dir`, além de
    `summary.csv`/`summary.json`/`execution.log` consolidados. Devolve o
    conteúdo de `summary.json`. Falha em um vídeo nunca interrompe o
    lote."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    handler = _attach_file_logger(output_dir)
    overall_t0 = time.perf_counter()

    try:
        logger.info("batch_started input_dir=%s output_dir=%s", input_dir, output_dir)

        if not input_dir.exists() or not input_dir.is_dir():
            message = f"Diretório não encontrado: {input_dir}"
            logger.error("batch_failed reason=%s", message)
            raise FileNotFoundError(message)

        video_paths = _discover_videos(input_dir)
        logger.info("videos_found count=%d", len(video_paths))

        summaries: list[dict] = []
        successful = 0
        failed = 0

        for index, video_path in enumerate(video_paths, start=1):
            video_output_dir = output_dir / f"video_{index:03d}"
            logger.info("video_started index=%d video=%s", index, video_path.name)
            video_t0 = time.perf_counter()
            try:
                summary = await run_validation(video_path, video_output_dir, ground_truth)
                summaries.append(summary)
                successful += 1
                logger.info("video_finished index=%d video=%s", index, video_path.name)
            except Exception as exc:
                execution_time = time.perf_counter() - video_t0
                summaries.append(_failure_summary(video_path, exc, execution_time))
                failed += 1
                logger.exception("video_failed index=%d video=%s", index, video_path.name)

        _write_summary_csv(output_dir / "summary.csv", summaries)
        stats = _write_summary_json(output_dir / "summary.json", summaries, successful, failed)

        logger.info(
            "batch_finished videos_processed=%d successful=%d failed=%d duration_seconds=%.2f",
            len(summaries), successful, failed, time.perf_counter() - overall_t0,
        )
        return stats
    except Exception:
        logger.exception("batch_aborted")
        raise
    finally:
        logger.removeHandler(handler)
        handler.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roda o Validation Runner (Fase 5A) para todos os vídeos de um diretório."
    )
    parser.add_argument("input_dir", help="Diretório contendo os vídeos a validar")
    parser.add_argument("--output-dir", default="validation_results", help="Diretório de saída (default: validation_results)")
    parser.add_argument("--ground-truth", default=None, help="Caminho de um JSON com o Ground Truth (opcional)")
    args = parser.parse_args()

    ground_truth = None
    if args.ground_truth:
        ground_truth = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))

    asyncio.run(run_batch_validation(args.input_dir, args.output_dir, ground_truth))


if __name__ == "__main__":
    main()
