"""Testes de ValidateJobStage - logica pura, sem I/O."""
from __future__ import annotations

import pytest

from worker.contracts.backend_api import JobDetails
from worker.core.exceptions import PipelineError
from worker.pipeline.stages.validate_job import ValidateJobStage


async def test_passes_through_when_job_is_consistent_and_not_terminal(base_state) -> None:
    base_state.job = JobDetails(id="job-1", video_id="video-1", status="QUEUED")

    result = await ValidateJobStage().run(base_state)

    assert result is base_state


async def test_raises_when_job_was_never_loaded(base_state) -> None:
    with pytest.raises(PipelineError):
        await ValidateJobStage().run(base_state)


async def test_raises_when_video_id_does_not_match(base_state) -> None:
    base_state.job = JobDetails(id="job-1", video_id="video-DIFERENTE", status="QUEUED")

    with pytest.raises(PipelineError):
        await ValidateJobStage().run(base_state)


@pytest.mark.parametrize("status", ["COMPLETED", "FAILED", "CANCELLED"])
async def test_raises_when_job_already_terminal(base_state, status: str) -> None:
    base_state.job = JobDetails(id="job-1", video_id="video-1", status=status)

    with pytest.raises(PipelineError):
        await ValidateJobStage().run(base_state)
