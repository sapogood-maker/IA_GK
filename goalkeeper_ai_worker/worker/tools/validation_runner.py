"""validation_runner: ferramenta OFFLINE de desenvolvedor para rodar um
video real, do inicio ao fim, pelo MESMO fluxo usado pelo Worker em
producao, e organizar os resultados num pacote completo de diagnostico
(Fase 5A, "Real World Validation Runner").

NAO e usada pelo Worker em producao nem pelo app Flutter - so por
desenvolvedores durante a fase de validacao. Nao modifica nenhuma das 11
camadas do Cognitive Core, o Runner, o WorkerOrchestrator, nenhuma Stage
nem o Pipeline - todos reutilizados EXATAMENTE como existem hoje.

Fluxo reproduzido (identico ao que `WorkerOrchestrator.process_job()`
executa para a parte de PROCESSAMENTO DE VIDEO - as etapas de Job/Queue/
Backend/Lock/Upload, que nao fazem sentido para um arquivo local sem Job
real, nao se aplicam e nao sao reproduzidas):

  InferenceStage.run(state)              # reutilizada sem alteracao
  -> run_cognitive_core_with_trace(...)  # a MESMA funcao que
     build_cognitive_report(...)         # CognitiveRunnerStage.run()
     analyze_cognitive_quality(...)      # chama - mesma ordem, mesmos
                                          # argumentos, mesma mesclagem
                                          # no artifact.json

Por que nao chamamos `CognitiveRunnerStage` diretamente: ela nao expoe o
Execution Trace (decisao de design da propria Stage, G2B/G2D) - so
devolve `state` com o artifact ja mesclado. Esta ferramenta PRECISA do
trace para produzir `error_analysis.json`/`improvement_recommendations.json`
(Fases 3B/4A/4B, que dependem de objetos internos do trace - hipoteses/
conviccoes/planos - nao apenas do artifact ja serializado). Chamar a
Stage E DEPOIS rodar a cadeia de novo para obter o trace executaria o
Cognitive Core duas vezes (exatamente o problema que a G2D eliminou) -
em vez disso, esta ferramenta chama as MESMAS funcoes que
`CognitiveRunnerStage.run()` chama, na MESMA ordem, com os MESMOS
argumentos, produzindo o artifact.json BYTE A BYTE identico ao que a
Stage produziria - e ainda tem o trace disponivel para os modulos de
Fase 3B/4A/4B, tudo com uma unica execucao do Core."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from worker.cognitive_runner.analyzer import analyze_cognitive_quality
from worker.cognitive_runner.error_mining import analyze_cognitive_errors
from worker.cognitive_runner.ground_truth import evaluate_against_ground_truth
from worker.cognitive_runner.improvement_recommender import recommend_improvements
from worker.cognitive_runner.report import build_cognitive_report
from worker.cognitive_runner.runner import run_cognitive_core_with_trace
from worker.config.settings import get_settings
from worker.inference.engine import create_engine
from worker.pipeline.stages.inference import InferenceStage
from worker.state.pipeline_state import PipelineState

logger = logging.getLogger("worker.tools.validation_runner")

OUTPUT_FILENAMES = (
    "artifact.json",
    "execution_summary.json",
    "quality.json",
    "error_analysis.json",
    "improvement_recommendations.json",
    "execution.log",
)


def _ensure_offline_settings() -> None:
    """A ferramenta nunca fala com um backend real (sem Job real) - so
    define valores minimos para satisfazer a validacao de `WorkerSettings`
    (que exige esses campos independentemente de uso). `setdefault` nunca
    sobrescreve um ambiente ja configurado (ex.: rodando dentro do
    conftest.py da suite de testes)."""
    os.environ.setdefault("WORKER_INSTANCE_ID", "validation-runner")
    os.environ.setdefault("WORKER_ENV", "validation")
    os.environ.setdefault("WORKER_BACKEND_API_URL", "http://validation-runner.invalid")
    os.environ.setdefault("WORKER_API_KEY", "validation-runner")


def _attach_file_logger(output_dir: Path) -> logging.Handler:
    handler = logging.FileHandler(output_dir / "execution.log", mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return handler


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _distinct_track_count(event_timeline: list[dict] | None) -> int:
    if not event_timeline:
        return 0
    return len({event["track_id"] for event in event_timeline if event.get("track_id") is not None})


async def run_validation(
    video_path: str | Path, output_dir: str | Path, ground_truth: list[dict] | None = None
) -> dict:
    """Roda o video real pelo mesmo fluxo do Worker e escreve o pacote de
    diagnostico completo em `output_dir`. Devolve o `execution_summary`
    (o mesmo conteudo gravado em `execution_summary.json`).

    `ground_truth` e opcional (aditivo ao enunciado - "Receber: caminho do
    vídeo" continua sendo a unica entrada obrigatoria): sem ele,
    `error_analysis.json`/`improvement_recommendations.json` ainda sao
    gerados normalmente, refletindo honestamente a ausencia de Ground
    Truth (todo segmento classificado como GROUND_TRUTH_MISMATCH,
    Fase 3B/4A) - nenhum valor e fabricado."""
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth = ground_truth if ground_truth is not None else []

    handler = _attach_file_logger(output_dir)
    errors: list[str] = []
    warnings: list[str] = []
    overall_t0 = time.perf_counter()

    try:
        logger.info("validation_started video=%s output_dir=%s", video_path, output_dir)

        if not video_path.exists():
            message = f"Video não encontrado: {video_path}"
            logger.error("validation_failed reason=%s", message)
            raise FileNotFoundError(message)

        _ensure_offline_settings()
        get_settings.cache_clear()
        settings = get_settings()

        state = PipelineState(
            job_id=f"validation-{uuid4()}",
            video_id=video_path.stem,
            message_id="0-1",
            started_at=datetime.now(timezone.utc),
            workspace_dir=output_dir,
            download_path=video_path,
        )

        logger.info("stage_started name=InferenceStage")
        t0 = time.perf_counter()
        state = await InferenceStage(create_engine(settings.inference_engine, settings)).run(state)
        logger.info("stage_finished name=InferenceStage duration_ms=%.2f", (time.perf_counter() - t0) * 1000)

        payload = json.loads(state.artifact_path.read_text(encoding="utf-8"))

        quality: dict | None = None
        report: dict | None = None
        error_analysis: dict | None = None
        recommendations: dict | None = None

        try:
            logger.info("stage_started name=CognitiveCore")
            t0 = time.perf_counter()
            results, trace = run_cognitive_core_with_trace(state.event_timeline)
            report = build_cognitive_report(trace)
            quality = analyze_cognitive_quality(trace)
            payload["cognitive_core_result"] = results
            payload["cognitive_core_metrics"] = report["metrics"]
            payload["cognitive_core_summary"] = report["summary"]
            payload["cognitive_quality"] = quality
            logger.info("stage_finished name=CognitiveCore duration_ms=%.2f", (time.perf_counter() - t0) * 1000)

            logger.info("stage_started name=GroundTruthEvaluation")
            gt_evaluation = evaluate_against_ground_truth(trace, results, ground_truth)
            if not ground_truth:
                warnings.append("Nenhum Ground Truth fornecido - error_analysis/improvement_recommendations "
                                 "refletem apenas divergências estruturais (GROUND_TRUTH_MISMATCH).")
            logger.info("stage_finished name=GroundTruthEvaluation")

            logger.info("stage_started name=ErrorMining")
            error_analysis = analyze_cognitive_errors(trace, gt_evaluation, quality)
            logger.info("stage_finished name=ErrorMining")

            logger.info("stage_started name=ImprovementRecommender")
            recommendations = recommend_improvements(trace, quality, gt_evaluation, error_analysis)
            logger.info("stage_finished name=ImprovementRecommender")
        except Exception as exc:  # noqa: BLE001 - isolamento deliberado (mesma filosofia de CognitiveRunnerStage)
            logger.exception("cognitive_analysis_failed")
            errors.append(f"cognitive_analysis_failed: {exc}")

        # state.artifact_path e sempre output_dir/"artifact.json" (workspace_dir=output_dir) -
        # esta e a UNICA escrita do artifact, tanto para o Worker quanto para esta ferramenta.
        state.artifact_path.write_text(json.dumps(payload), encoding="utf-8")

        if quality is not None:
            _write_json(output_dir / "quality.json", payload["cognitive_quality"])
        if error_analysis is not None:
            _write_json(output_dir / "error_analysis.json", error_analysis)
        if recommendations is not None:
            _write_json(output_dir / "improvement_recommendations.json", recommendations)

        execution_summary = {
            "video": str(video_path),
            "duration": payload.get("frame_metadata", {}).get("duration_seconds"),
            "frames": payload.get("frames_processed"),
            "tracks": _distinct_track_count(state.event_timeline),
            "play_segments": report["metrics"]["counts"]["play_segments"] if report is not None else 0,
            "decisions": report["metrics"]["counts"]["decision_count"] if report is not None else 0,
            "execution_time": time.perf_counter() - overall_t0,
            "errors": errors,
            "warnings": warnings,
        }
        _write_json(output_dir / "execution_summary.json", execution_summary)

        logger.info(
            "validation_finished duration_seconds=%.2f errors=%d warnings=%d",
            execution_summary["execution_time"], len(errors), len(warnings),
        )
        return execution_summary
    except Exception:
        logger.exception("validation_aborted")
        raise
    finally:
        logger.removeHandler(handler)
        handler.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Roda um video real pelo mesmo fluxo do Worker (Fase 5A).")
    parser.add_argument("video_path", help="Caminho do video a validar")
    parser.add_argument("--output-dir", default="validation_output", help="Diretório de saída (default: validation_output)")
    parser.add_argument("--ground-truth", default=None, help="Caminho de um JSON com o Ground Truth (opcional)")
    args = parser.parse_args()

    ground_truth = None
    if args.ground_truth:
        ground_truth = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))

    asyncio.run(run_validation(args.video_path, args.output_dir, ground_truth))


if __name__ == "__main__":
    main()
