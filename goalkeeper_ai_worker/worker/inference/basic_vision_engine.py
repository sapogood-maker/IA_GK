"""BasicVisionEngine: motor de visão computacional básica.

Sprint W7: deixou de executar resize/ROI/conversão de cor diretamente —
agora é um **orquestrador**. Toda transformação de imagem acontece em
Processors independentes (`inference/processors/`), coordenados por
`PipelineProcessor`. Este motor apenas: recebe frames do `FrameProvider`,
executa a `PipelineProcessor`, gera o artefato. Nenhuma lógica de
transformação duplicada aqui.

Sprint W8: detecção real passou a existir (`YOLOProcessor`, quando
habilitado via `WORKER_DETECTOR`) - mas o motor continua sem saber nada
disso além de ler `context.detections` de volta, exatamente como já lia
`context.stats`. Nenhum código de detecção/modelo vive aqui.

Sprint W9: tracking real passou a existir (`TrackingProcessor`, quando
habilitado via `WORKER_TRACKER`/`WORKER_TRACKING_ENABLED`) - mesma
disciplina: o motor só lê `context.tracking_results` de volta. Como a
mesma instância deste motor (e da `PipelineProcessor` que ele contém) é
reaproveitada por todo o ciclo de vida do processo do Worker (construída
uma vez em `WorkerOrchestrator.__init__`, não por Job), o motor chama
`self._pipeline.reset()` no início de cada Job - sem isso, um Tracker
stateful vazaria identidade de trilhas de um vídeo para o próximo.

Sprint W10: interpretação de cena real passou a existir
(`SceneAnalysisProcessor`, quando habilitado via `WORKER_SCENE_ANALYZER`/
`WORKER_SCENE_ANALYSIS_ENABLED`) - mesma disciplina: o motor só lê
`context.scene_analysis_results` de volta. Nenhuma regra de negócio de
futebol vive aqui nem em nenhum Processor - só eventos genéricos de cena.

**Nenhuma classificação/pose/regra de negócio de futebol** — fica para sprints futuras.
"""
from __future__ import annotations

import json
import time

from worker.config.settings import WorkerSettings
from worker.inference.base import InferenceEngine
from worker.inference.exceptions import InferenceExecutionError
from worker.inference.processors.base import ProcessorContext
from worker.inference.processors.pipeline import PipelineProcessor
from worker.inference.types import FrameMetadata, InferenceMetadata, InferenceResult, RegionOfInterest
from worker.state.pipeline_state import PipelineState
from worker.video.exceptions import VideoError
from worker.video.iterator import FrameIterator
from worker.video.provider import FrameProvider
from worker.video.reader import VideoReader


class BasicVisionEngine(InferenceEngine):
    """Orquestrador de visão computacional básica — nenhuma transformação
    de imagem vive aqui, só a delegação à `PipelineProcessor`."""

    name = "basic_vision"
    version = "2.0.0"

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._pipeline = PipelineProcessor.from_settings(settings)
        self._frame_skip = settings.frame_skip

    def _should_process(self, frame_index: int) -> bool:
        """Decide se este índice de frame deve ser processado, dado o
        frame_skip. Permanece no motor, não em um Processor - decidir
        SE um frame entra na pipeline é diferente de TRANSFORMAR um frame."""
        return frame_index % (self._frame_skip + 1) == 0

    async def process(self, state: PipelineState) -> PipelineState:
        if state.download_path is None or not state.download_path.exists():
            raise InferenceExecutionError(
                f"Video baixado nao encontrado em {state.download_path}"
            )

        self._pipeline.reset()

        start = time.monotonic()
        context = ProcessorContext()
        last_metadata: FrameMetadata | None = None
        try:
            with VideoReader(state.download_path) as reader:
                provider = FrameProvider(reader)
                properties = reader.properties
                frames_processed = 0

                for frame in FrameIterator(provider):
                    if not self._should_process(frame.metadata.frame_index):
                        continue

                    _, last_metadata, context = self._pipeline.process(
                        frame.image, frame.metadata, context
                    )
                    frames_processed += 1
        except VideoError as exc:
            raise InferenceExecutionError(f"Falha ao ler o video: {exc}") from exc

        duration_ms = (time.monotonic() - start) * 1000

        final_width = last_metadata.width if last_metadata is not None else properties.width
        final_height = last_metadata.height if last_metadata is not None else properties.height

        roi = (
            RegionOfInterest(
                x=self._settings.roi_x,
                y=self._settings.roi_y,
                width=self._settings.roi_width,
                height=self._settings.roi_height,
            )
            if self._settings.enable_roi
            else None
        )

        result = InferenceResult(
            status="processed",
            detections=[],
            frame_metadata=FrameMetadata(
                frame_count=properties.frame_count,
                width=final_width,
                height=final_height,
                fps=properties.fps,
                duration_seconds=properties.duration_seconds,
            ),
            metadata=InferenceMetadata(
                engine_name=self.name, engine_version=self.version, duration_ms=duration_ms
            ),
            frames_processed=frames_processed,
            frame_skip=self._frame_skip,
            roi=roi,
        )

        payload = result.to_dict()
        payload["processors"] = context.to_dict()
        payload["processor_order"] = self._pipeline.processor_names
        payload["detection_results"] = context.detections_to_dict()
        payload["tracking_results"] = context.tracking_results_to_dict()
        if context.tracking_results:
            last_tracking_result = context.tracking_results[-1]
            payload["tracking_engine"] = last_tracking_result.tracker_name
            payload["tracking_statistics"] = last_tracking_result.statistics.to_dict()
        else:
            payload["tracking_engine"] = None
            payload["tracking_statistics"] = None
        payload["tracking_time_ms"] = (
            context.stats["tracking"].total_time_ms if "tracking" in context.stats else 0.0
        )
        payload["scene_events"] = context.scene_events_to_dict()
        payload["scene_statistics"] = (
            context.scene_analysis_results[-1].statistics.to_dict()
            if context.scene_analysis_results
            else None
        )
        payload["scene_processing_time_ms"] = (
            context.stats["scene_analysis"].total_time_ms if "scene_analysis" in context.stats else 0.0
        )

        artifact_path = state.workspace_dir / "artifact.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")

        state.artifact_path = artifact_path
        state.inference_result = result
        return state
