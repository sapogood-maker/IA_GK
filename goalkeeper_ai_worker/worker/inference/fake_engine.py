"""FakeInferenceEngine: substitui completamente o antigo FakeProcessingStage
(e absorve a responsabilidade do antigo GenerateArtifactStage - o motor e
quem decide o formato do proprio resultado, incluindo como salva-lo).

Sprint W5: consome `worker.video` (VideoReader/FrameProvider/FrameIterator)
em vez de ler bytes crus do arquivo - conta os frames de verdade e le
fps/dimensoes/duracao reais, mas continua sem qualquer analise de
conteudo. Nao usa OpenCV como mecanismo de inferencia - so como biblioteca
de leitura de vídeo, via worker.video (Boundary interno: inference/ nunca
abre o arquivo de vídeo diretamente, so consome FrameProvider/FrameIterator).

Sprint W6: ganhou `__init__(settings)` para manter o mesmo formato de
construtor de qualquer motor registrado (uniformidade exigida por
`engine.create_engine`) - `settings` nao e usado, pois este motor nao tem
nenhuma configuracao propria. Deixou de ser o motor padrao
(`WORKER_INFERENCE_ENGINE`), mas continua registrado para os testes que
nao precisam de processamento real de frame.
"""
from __future__ import annotations

import json
import time

from worker.config.settings import WorkerSettings
from worker.inference.base import InferenceEngine
from worker.inference.exceptions import InferenceExecutionError
from worker.inference.types import FrameMetadata, InferenceMetadata, InferenceResult
from worker.state.pipeline_state import PipelineState
from worker.video.exceptions import VideoError
from worker.video.iterator import FrameIterator
from worker.video.provider import FrameProvider
from worker.video.reader import VideoReader


class FakeInferenceEngine(InferenceEngine):
    """Motor de inferencia placeholder - conta frames via FrameProvider,
    sem nenhuma deteccao ou analise de conteudo."""

    name = "fake"
    version = "0.2.0"

    def __init__(self, settings: WorkerSettings | None = None) -> None:
        self._settings = settings

    async def process(self, state: PipelineState) -> PipelineState:
        if state.download_path is None or not state.download_path.exists():
            raise InferenceExecutionError(
                f"Video baixado nao encontrado em {state.download_path}"
            )

        start = time.monotonic()
        try:
            with VideoReader(state.download_path) as reader:
                provider = FrameProvider(reader)
                frame_count = 0
                for _ in FrameIterator(provider):
                    frame_count += 1
                properties = reader.properties
        except VideoError as exc:
            raise InferenceExecutionError(f"Falha ao ler o video: {exc}") from exc

        duration_ms = (time.monotonic() - start) * 1000

        result = InferenceResult(
            status="processed",
            detections=[],
            frame_metadata=FrameMetadata(
                frame_count=frame_count,
                width=properties.width,
                height=properties.height,
                fps=properties.fps,
                duration_seconds=properties.duration_seconds,
            ),
            metadata=InferenceMetadata(
                engine_name=self.name, engine_version=self.version, duration_ms=duration_ms
            ),
        )

        artifact_path = state.workspace_dir / "artifact.json"
        artifact_path.write_text(json.dumps(result.to_dict()), encoding="utf-8")

        state.artifact_path = artifact_path
        state.inference_result = result
        return state
