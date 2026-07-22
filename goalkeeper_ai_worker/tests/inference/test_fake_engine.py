"""Testes de worker.inference.fake_engine.FakeInferenceEngine.

Sprint W5: agora consome vídeo real via VideoReader/FrameProvider/
FrameIterator (worker.video), não mais bytes crus - integração real, não
mockada, entre inference/ e video/.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.conftest import REAL_VIDEO_FPS, REAL_VIDEO_FRAME_COUNT, REAL_VIDEO_HEIGHT, REAL_VIDEO_WIDTH
from worker.inference.exceptions import InferenceExecutionError
from worker.inference.fake_engine import FakeInferenceEngine
from worker.state.pipeline_state import PipelineState


def _make_state(tmp_path: Path, video_path: Path | None) -> PipelineState:
    state = PipelineState(
        job_id="job-1", video_id="video-1", message_id="0-1", started_at=datetime.now(timezone.utc)
    )
    state.workspace_dir = tmp_path
    if video_path is not None:
        download_path = tmp_path / "input_video"
        shutil.copy(video_path, download_path)
        state.download_path = download_path
    return state


async def test_process_reads_real_video_and_writes_artifact(
    tmp_path: Path, real_video_path: Path
) -> None:
    state = _make_state(tmp_path, real_video_path)

    result = await FakeInferenceEngine().process(state)

    assert result.artifact_path is not None
    assert result.artifact_path.exists()
    assert result.inference_result is not None
    assert result.inference_result.frame_metadata.frame_count == REAL_VIDEO_FRAME_COUNT
    assert result.inference_result.frame_metadata.fps == pytest.approx(REAL_VIDEO_FPS, rel=0.1)
    assert result.inference_result.frame_metadata.width == REAL_VIDEO_WIDTH
    assert result.inference_result.frame_metadata.height == REAL_VIDEO_HEIGHT

    saved = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert saved["frame_metadata"]["frame_count"] == REAL_VIDEO_FRAME_COUNT
    assert saved["metadata"]["engine_name"] == "fake"


async def test_process_raises_when_download_path_missing(tmp_path: Path) -> None:
    state = _make_state(tmp_path, None)

    with pytest.raises(InferenceExecutionError):
        await FakeInferenceEngine().process(state)


async def test_process_raises_for_corrupted_video(tmp_path: Path, corrupted_video_path: Path) -> None:
    state = _make_state(tmp_path, corrupted_video_path)

    with pytest.raises(InferenceExecutionError):
        await FakeInferenceEngine().process(state)
