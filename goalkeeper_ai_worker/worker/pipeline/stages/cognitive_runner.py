"""CognitiveRunnerStage: conecta worker/cognitive_runner/ ao Pipeline real
(Phase 2, G2B/G2C/G2D).

Roda entre InferenceStage e UploadArtifactStage: chama
run_cognitive_core_with_trace() sobre o event_timeline ja em memoria
(state.event_timeline, Phase 2/G2A) e mescla o resultado no MESMO
artifact.json ja escrito por InferenceStage, sob a chave
`cognitive_core_result` (G2B), alem de `cognitive_core_metrics`/
`cognitive_core_summary` (G2C) - observabilidade pura, nenhuma decisao
nova, nenhuma chave existente alterada.

G2D: o Cognitive Core roda exatamente UMA VEZ por Job -
run_cognitive_core_with_trace() devolve `results` (identico ao que
run_cognitive_core() sempre devolveu) e o Execution Trace, que
build_cognitive_report() consome diretamente (sem recomputar a cadeia).

Estagio observacional: o entregavel essencial do Job (deteccao/tracking/
analyzers no artifact.json) ja existe antes desta Stage rodar. Por isso,
diferente de toda outra Stage do pipeline, uma falha aqui NUNCA propaga -
e apenas logada (com stacktrace via logger.exception) - e o Job continua
normalmente ate UploadArtifactStage/UpdateStatusStage, com o artifact
original (sem as chaves cognitivas). Decisao formalizada e aprovada no
plano de integracao da G2A (Secao 3-B). As chaves cognitivas sao mescladas
todas de uma vez (mesmo try/except) - uma falha em qualquer parte (Runner
ou Report) descarta as duas, nunca um artifact com metrics mas sem result.
"""
from __future__ import annotations

import json
import logging

from worker.cognitive_runner.report import build_cognitive_report
from worker.cognitive_runner.runner import run_cognitive_core_with_trace
from worker.state.pipeline_state import PipelineState

logger = logging.getLogger(__name__)


class CognitiveRunnerStage:
    """Unica responsabilidade: rodar o Cognitive Core sobre o event_timeline
    real e mesclar `cognitive_core_result`/`cognitive_core_metrics`/
    `cognitive_core_summary` no artifact.json ja existente."""

    async def run(self, state: PipelineState) -> PipelineState:
        try:
            results, trace = run_cognitive_core_with_trace(state.event_timeline)
            report = build_cognitive_report(trace)

            payload = json.loads(state.artifact_path.read_text(encoding="utf-8"))
            payload["cognitive_core_result"] = results
            payload["cognitive_core_metrics"] = report["metrics"]
            payload["cognitive_core_summary"] = report["summary"]
            state.artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            logger.exception(
                "cognitive_runner_failed job_id=%s video_id=%s", state.job_id, state.video_id
            )

        return state
