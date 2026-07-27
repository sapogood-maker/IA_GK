"""Teste de wiring do WorkerOrchestrator (Phase 2, G2B): confirma que
CognitiveRunnerStage e chamada, e chamada exatamente entre InferenceStage e
UploadArtifactStage. Nao usa Redis/video reais - substitui todos os Stages
internos por dublês que so registram ordem de chamada, evitando a
dependencia de infraestrutura externa (Redis real, container de teste) que
o teste de integracao completo (`test_orchestrator_pipeline.py`) exige."""
from __future__ import annotations

import httpx

from worker.config.settings import get_settings
from worker.contracts.queue_message import JobMessage
from worker.infrastructure.backend_client.client import BackendClient
from worker.orchestrator.orchestrator import WorkerOrchestrator
from worker.pipeline.stages.cognitive_runner import CognitiveRunnerStage


class _RecordingStage:
    def __init__(self, name: str, call_order: list[str]) -> None:
        self._name = name
        self._call_order = call_order

    async def run(self, state):
        self._call_order.append(self._name)
        return state


async def test_orchestrator_wires_a_cognitive_runner_stage() -> None:
    settings = get_settings()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    backend_client = BackendClient(settings, transport=transport)

    orchestrator = WorkerOrchestrator(settings, redis_client=object(), backend_client=backend_client, transport=transport)

    assert isinstance(orchestrator._cognitive_runner, CognitiveRunnerStage)

    await backend_client.aclose()


async def test_cognitive_runner_stage_runs_between_inference_and_upload_artifact() -> None:
    settings = get_settings()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    backend_client = BackendClient(settings, transport=transport)
    orchestrator = WorkerOrchestrator(settings, redis_client=object(), backend_client=backend_client, transport=transport)

    call_order: list[str] = []
    for attr in (
        "_receive_job", "_validate_job", "_acquire_lock", "_prepare_workspace",
        "_download_video", "_inference", "_cognitive_runner", "_upload_artifact",
        "_update_status", "_cleanup", "_release_lock",
    ):
        setattr(orchestrator, attr, _RecordingStage(attr, call_order))

    message = JobMessage(message_id="0-1", job_id="job-1", video_id="video-1")
    result = await orchestrator.process_job(message)

    assert call_order == [
        "_receive_job", "_validate_job", "_acquire_lock", "_prepare_workspace",
        "_download_video", "_inference", "_cognitive_runner", "_upload_artifact",
        "_update_status", "_cleanup", "_release_lock",
    ]
    assert result.status == "COMPLETED"

    await backend_client.aclose()
