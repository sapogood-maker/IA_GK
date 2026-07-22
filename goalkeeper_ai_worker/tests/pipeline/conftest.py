"""Fixtures compartilhadas dos testes unitarios de Stages do Pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worker.state.pipeline_state import PipelineState


@pytest.fixture
def base_state() -> PipelineState:
    """PipelineState minimo, antes de qualquer Stage rodar."""
    return PipelineState(
        job_id="job-1",
        video_id="video-1",
        message_id="0-1",
        started_at=datetime.now(timezone.utc),
    )
