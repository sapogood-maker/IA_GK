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

Sprint W11: o World Model passou a existir (`WorldModelProcessor`, quando
habilitado via `WORKER_WORLD_MODEL`/`WORKER_WORLD_MODEL_ENABLED`) - mesma
disciplina: o motor só lê `context.world_states` de volta. Esta foi a
ÚLTIMA camada GENÉRICA da arquitetura de visão computacional.

Sprint W12: o Football Domain Model passou a existir
(`FootballDomainProcessor`, quando habilitado via
`WORKER_FOOTBALL_DOMAIN_ENABLED`) - primeira camada ESPECÍFICA do domínio
de futebol (`worker/domain/`, pacote irmão de `inference/`, não um
submódulo dele). Mesma disciplina: o motor só lê
`context.football_worlds` de volta. Nenhuma regra de negócio/heurística
de futebol vive aqui nem em `FootballDomainProcessor` - só transformação
estrutural de `WorldState` em `FootballWorld`.

Sprint W13: a Analyzer API passou a existir (`AnalyzerProcessor`, quando
`WORKER_ANALYZERS` não está vazio) - primeira camada de ANÁLISE
propriamente dita, mas mesma disciplina: o motor só lê
`context.analysis_results` de volta. `worker/analyzers/` é módulo irmão
de `worker/domain/`, não um submódulo dele.

Sprint W14: `GoalGeometryAnalyzer` (segundo Analyzer registrado, puramente
geométrico) não exigiu NENHUMA mudança nesta classe além de mais uma
chave de conveniência no artefato (`"goal_geometry_result"`, um alias
para `analysis_results["goal_geometry"]`) - confirma na prática que
adicionar um novo Analyzer nunca toca no motor.

Sprint W15: `GoalkeeperPositionAnalyzer` (terceiro Analyzer, compõe
`GoalGeometryAnalyzer` internamente) - mesma disciplina: mais uma chave
de conveniência (`"goalkeeper_position_result"`), nenhuma mudança
estrutural.

Sprint W16: `BallPositionAnalyzer` (quarto Analyzer, mesmo padrão de
composição da W15) - mais uma chave de conveniência
(`"ball_position_result"`), nenhuma mudança estrutural.

Sprint W17: `GoalkeeperBallAlignmentAnalyzer` (quinto Analyzer, primeiro
RELACIONAL - compõe os três Analyzers anteriores internamente) - mais
uma chave de conveniência (`"goalkeeper_ball_alignment_result"`),
nenhuma mudança estrutural.

Sprint W18: `BallMotionAnalyzer` (sexto Analyzer, primeiro STATEFUL -
mede movimento observado da bola entre frames) - mesma disciplina: mais
uma chave de conveniência (`"ball_motion_result"`). O motor continua
sem saber que esse Analyzer tem estado - `AnalyzerProcessor.reset()`
(já existente desde a W13) já delega a `analyzer.reset()` de cada
Analyzer ativo, sem nenhuma mudança aqui.

Sprint W19: `ShotAnalyzer` (sétimo Analyzer, primeiro de EVENTOS -
identifica se houve um evento compatível com um chute, via critérios
determinísticos parametrizáveis) - mesma disciplina: mais uma chave de
conveniência (`"shot_analysis_result"`), nenhuma mudança estrutural.

Sprint W20: `BallTrajectoryAnalyzer` (oitavo Analyzer, segundo STATEFUL -
modela a trajetória observada da bola ao longo de múltiplos frames) -
mesma disciplina: mais uma chave de conveniência
(`"ball_trajectory_result"`), nenhuma mudança estrutural.

Sprint W21: `PlaySituationAnalyzer` (nono Analyzer, primeiro COGNITIVO -
classifica o estado observado da jogada, combinando quatro Analyzers
já existentes) - mesma disciplina: mais uma chave de conveniência
(`"play_situation_result"`), nenhuma mudança estrutural.

Sprint W22: `GoalkeeperDecisionAnalyzer` (décimo Analyzer, primeiro
específico do goleiro - identifica qual decisão o goleiro aparenta estar
executando, combinando cinco Analyzers já existentes) - mesma
disciplina: mais uma chave de conveniência
(`"goalkeeper_decision_result"`), nenhuma mudança estrutural.

Sprint W23: `GoalkeeperDecisionEvaluationAnalyzer` (décimo primeiro
Analyzer, primeiro de AVALIAÇÃO - responde se a decisão observada do
goleiro foi compatível com a situação observada, via um mecanismo
explícito de Rule Evaluation) - mesma disciplina: mais uma chave de
conveniência (`"goalkeeper_decision_evaluation_result"`), nenhuma
mudança estrutural.

Sprint W24: `PlayOutcomeAnalyzer` (décimo segundo Analyzer, encerra a
cadeia de observação - responde qual foi o resultado observado da
jogada, combinando cinco Analyzers já existentes) - mesma disciplina:
mais uma chave de conveniência (`"play_outcome_result"`), nenhuma
mudança estrutural.

Sprint W25: `GoalkeeperPerformanceEvaluationAnalyzer` (décimo terceiro
Analyzer, encerra a cadeia de avaliação - responde como foi o
desempenho observado do goleiro, combinando `GoalkeeperDecisionEvaluationResult`/
`PlayOutcomeResult` via Rule Evaluation, W23) - mesma disciplina: mais
uma chave de conveniência (`"goalkeeper_performance_evaluation_result"`),
nenhuma mudança estrutural.

Sprint W26: `GoalkeeperCoachingAnalyzer` (décimo quarto Analyzer,
primeiro de COACHING - responde qual orientação técnica pode ser
extraída da jogada, combinando `GoalkeeperPerformanceEvaluationResult`/
`GoalkeeperDecisionEvaluationResult.rules_failed`/`GoalkeeperDecisionResult`/
`PlayOutcomeResult` via a MESMA Rule Evaluation da W23) - mesma
disciplina: mais uma chave de conveniência
(`"goalkeeper_coaching_result"`), nenhuma mudança estrutural.

Sprint W27: `GoalkeeperAnalysisReportAnalyzer` (décimo quinto Analyzer,
encerra oficialmente o MVP arquitetural - agrega, sem recalcular nada,
os seis resultados cognitivos já produzidos - `PlaySituationResult`/
`GoalkeeperDecisionResult`/`GoalkeeperDecisionEvaluationResult`/
`PlayOutcomeResult`/`GoalkeeperPerformanceEvaluationResult`/
`GoalkeeperCoachingResult` - num único `GoalkeeperAnalysisReport`, o
CONTRATO OFICIAL de saída do Worker) - mesma disciplina: mais uma chave
de conveniência (`"goalkeeper_analysis_report"`), nenhuma mudança
estrutural.
"""
from __future__ import annotations

import json
import time

from worker.analyzers.results import AnalysisStatistics
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
        if context.world_states:
            last_world_state = context.world_states[-1]
            payload["world_state"] = last_world_state.to_dict()
            payload["world_statistics"] = last_world_state.statistics.to_dict()
            payload["object_count"] = last_world_state.statistics.object_count
            payload["active_tracks"] = last_world_state.statistics.active_tracks
            payload["lost_tracks"] = last_world_state.statistics.lost_tracks
            payload["average_speed"] = last_world_state.statistics.average_speed
        else:
            payload["world_state"] = None
            payload["world_statistics"] = None
            payload["object_count"] = 0
            payload["active_tracks"] = 0
            payload["lost_tracks"] = 0
            payload["average_speed"] = 0.0
        payload["processing_time_ms"] = (
            context.stats["world_model"].total_time_ms if "world_model" in context.stats else 0.0
        )
        payload["football_world"] = (
            context.football_worlds[-1].to_dict() if context.football_worlds else None
        )
        payload["football_domain_time_ms"] = (
            context.stats["football_domain"].total_time_ms if "football_domain" in context.stats else 0.0
        )

        latest_results_by_analyzer: dict[str, dict] = {}
        for analysis_result in context.analysis_results:
            latest_results_by_analyzer[analysis_result.metadata.analyzer_name] = analysis_result.to_dict()
        payload["analysis_results"] = latest_results_by_analyzer
        payload["analysis_statistics"] = AnalysisStatistics(
            analyzers_run=sorted(latest_results_by_analyzer),
            results_count=len(latest_results_by_analyzer),
        ).to_dict()
        payload["analyzer_processing_time_ms"] = (
            context.stats["analyzer"].total_time_ms if "analyzer" in context.stats else 0.0
        )
        payload["goal_geometry_result"] = latest_results_by_analyzer.get("goal_geometry")
        payload["goalkeeper_position_result"] = latest_results_by_analyzer.get("goalkeeper_position")
        payload["ball_position_result"] = latest_results_by_analyzer.get("ball_position")
        payload["goalkeeper_ball_alignment_result"] = latest_results_by_analyzer.get("goalkeeper_ball_alignment")
        payload["ball_motion_result"] = latest_results_by_analyzer.get("ball_motion")
        payload["shot_analysis_result"] = latest_results_by_analyzer.get("shot")
        payload["ball_trajectory_result"] = latest_results_by_analyzer.get("ball_trajectory")
        payload["play_situation_result"] = latest_results_by_analyzer.get("play_situation")
        payload["goalkeeper_decision_result"] = latest_results_by_analyzer.get("goalkeeper_decision")
        payload["goalkeeper_decision_evaluation_result"] = latest_results_by_analyzer.get(
            "goalkeeper_decision_evaluation"
        )
        payload["play_outcome_result"] = latest_results_by_analyzer.get("play_outcome")
        payload["goalkeeper_performance_evaluation_result"] = latest_results_by_analyzer.get(
            "goalkeeper_performance_evaluation"
        )
        payload["goalkeeper_coaching_result"] = latest_results_by_analyzer.get("goalkeeper_coaching")
        payload["goalkeeper_analysis_report"] = latest_results_by_analyzer.get("goalkeeper_analysis_report")

        artifact_path = state.workspace_dir / "artifact.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")

        state.artifact_path = artifact_path
        state.inference_result = result
        return state
