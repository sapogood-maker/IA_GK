"""WorkerOrchestrator: coordena o Pipeline de processamento de um Job.

Nunca implementa regra de negocio - so chama os Stages corretos, na ordem
certa, e garante que Cleanup/ReleaseLock rodem mesmo em caso de falha
(bloco finally). AI_WORKER_CONSTITUTION.md, Secao 1 e 2.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from worker.config.settings import WorkerSettings
from worker.contracts.queue_message import JobMessage
from worker.core.exceptions import WorkerError
from worker.events.events import JobCompleted, JobFailed, emit
from worker.infrastructure.backend_client.client import BackendClient
from worker.infrastructure.redis.consumer import ack_job, ensure_consumer_group, read_next_job
from worker.inference.engine import create_engine
from worker.pipeline.stages.acquire_lock import AcquireLockStage
from worker.pipeline.stages.cleanup import CleanupStage
from worker.pipeline.stages.cognitive_runner import CognitiveRunnerStage
from worker.pipeline.stages.download_video import DownloadVideoStage
from worker.pipeline.stages.inference import InferenceStage
from worker.pipeline.stages.prepare_workspace import PrepareWorkspaceStage
from worker.pipeline.stages.receive_job import ReceiveJobStage
from worker.pipeline.stages.release_lock import ReleaseLockStage
from worker.pipeline.stages.update_status import UpdateStatusStage
from worker.pipeline.stages.upload_artifact import UploadArtifactStage
from worker.pipeline.stages.validate_job import ValidateJobStage
from worker.state.pipeline_state import PipelineState
from worker.workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)


class WorkerOrchestrator:
    """Coordena o fluxo do Pipeline. Nao decide regra de negocio - so chama
    os componentes corretos, na ordem certa."""

    def __init__(
        self,
        settings: WorkerSettings,
        redis_client,
        backend_client: BackendClient,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._redis_client = redis_client
        workspace_manager = WorkspaceManager()

        self._receive_job = ReceiveJobStage(backend_client)
        self._validate_job = ValidateJobStage()
        self._acquire_lock = AcquireLockStage(redis_client, settings.instance_id, settings.lock_ttl_seconds)
        self._prepare_workspace = PrepareWorkspaceStage(workspace_manager)
        self._download_video = DownloadVideoStage(backend_client, transport=transport)
        self._inference = InferenceStage(create_engine(settings.inference_engine, settings))
        self._cognitive_runner = CognitiveRunnerStage()
        self._upload_artifact = UploadArtifactStage(backend_client, transport=transport)
        self._update_status = UpdateStatusStage(backend_client, settings.instance_id)
        self._cleanup = CleanupStage(workspace_manager)
        self._release_lock = ReleaseLockStage(redis_client, settings.instance_id)

    async def process_job(self, message: JobMessage) -> PipelineState:
        """Executa o Pipeline completo para um Job.

        Garante Cleanup e ReleaseLock mesmo se qualquer Stage anterior
        falhar (bloco finally) - sem retry automatico e sem rollback
        complexo (Sprint W3)."""
        state = PipelineState(
            job_id=message.job_id,
            video_id=message.video_id,
            message_id=message.message_id,
            started_at=datetime.now(timezone.utc),
        )
        try:
            state = await self._receive_job.run(state)
            state = await self._validate_job.run(state)
            state = await self._acquire_lock.run(state)
            state = await self._prepare_workspace.run(state)
            state = await self._download_video.run(state)
            state = await self._inference.run(state)
            state = await self._cognitive_runner.run(state)
            state = await self._upload_artifact.run(state)
            state = await self._update_status.run(state)
            state.status = "COMPLETED"
            emit(JobCompleted(job_id=state.job_id, video_id=state.video_id))
        except WorkerError as exc:
            state.status = "FAILED"
            state.errors.append(str(exc))
            emit(JobFailed(job_id=state.job_id, video_id=state.video_id, error=str(exc)))
            logger.error(
                "job_failed job_id=%s video_id=%s error=%s", state.job_id, state.video_id, exc
            )
        finally:
            state = await self._cleanup.run(state)
            state = await self._release_lock.run(state)

        state.finished_at = datetime.now(timezone.utc)
        return state

    async def run_forever(self, shutdown_event: asyncio.Event) -> None:
        """Consome Jobs do Redis continuamente ate o shutdown_event ser
        sinalizado. Sem retry automatico, sem heartbeat continuo, sem
        scheduler (Sprint W3) - cada mensagem lida e processada e depois
        confirmada (ACK), com sucesso ou falha."""
        await ensure_consumer_group(self._redis_client, self._settings.consumer_group)
        while not shutdown_event.is_set():
            message = await read_next_job(
                self._redis_client,
                self._settings.consumer_group,
                self._settings.instance_id,
                block_ms=2000,
            )
            if message is None:
                continue
            await self.process_job(message)
            await ack_job(self._redis_client, self._settings.consumer_group, message.message_id)
