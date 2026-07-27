"""CognitiveRunnerStage: conecta worker/cognitive_runner/ ao Pipeline real
(Phase 2, G2B).

Roda entre InferenceStage e UploadArtifactStage: chama run_cognitive_core()
sobre o event_timeline ja em memoria (state.event_timeline, Phase 2/G2A) e
mescla o resultado no MESMO artifact.json ja escrito por InferenceStage, sob
a chave nova `cognitive_core_result` - nenhuma outra chave e alterada.

Estagio observacional: o entregavel essencial do Job (deteccao/tracking/
analyzers no artifact.json) ja existe antes desta Stage rodar. Por isso,
diferente de toda outra Stage do pipeline, uma falha aqui NUNCA propaga -
e apenas logada (com stacktrace via logger.exception) - e o Job continua
normalmente ate UploadArtifactStage/UpdateStatusStage, com o artifact
original (sem cognitive_core_result). Decisao formalizada e aprovada no
plano de integracao da G2A (Secao 3-B).
"""
from __future__ import annotations

import json
import logging

from worker.cognitive_runner.runner import run_cognitive_core
from worker.state.pipeline_state import PipelineState

logger = logging.getLogger(__name__)


class CognitiveRunnerStage:
    """Unica responsabilidade: rodar o Cognitive Core sobre o event_timeline
    real e mesclar `cognitive_core_result` no artifact.json ja existente."""

    async def run(self, state: PipelineState) -> PipelineState:
        try:
            results = run_cognitive_core(state.event_timeline)

            payload = json.loads(state.artifact_path.read_text(encoding="utf-8"))
            payload["cognitive_core_result"] = results
            state.artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            logger.exception(
                "cognitive_runner_failed job_id=%s video_id=%s", state.job_id, state.video_id
            )

        return state
