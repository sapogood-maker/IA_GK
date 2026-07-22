"""Testes de VideoReader - vídeos reais gerados com OpenCV, nunca mockados."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import REAL_VIDEO_FPS, REAL_VIDEO_FRAME_COUNT, REAL_VIDEO_HEIGHT, REAL_VIDEO_WIDTH
from worker.video.exceptions import InvalidVideoError, VideoOpenError
from worker.video.reader import VideoReader


def test_open_reads_real_properties(real_video_path: Path) -> None:
    reader = VideoReader(real_video_path)
    reader.open()
    try:
        props = reader.properties
        assert props.frame_count == REAL_VIDEO_FRAME_COUNT
        assert props.fps == pytest.approx(REAL_VIDEO_FPS, rel=0.1)
        assert props.width == REAL_VIDEO_WIDTH
        assert props.height == REAL_VIDEO_HEIGHT
        assert props.duration_seconds == pytest.approx(
            REAL_VIDEO_FRAME_COUNT / REAL_VIDEO_FPS, rel=0.2
        )
    finally:
        reader.close()


def test_open_raises_when_file_does_not_exist(missing_video_path: Path) -> None:
    reader = VideoReader(missing_video_path)
    with pytest.raises(VideoOpenError):
        reader.open()


def test_open_raises_for_corrupted_file(corrupted_video_path: Path) -> None:
    reader = VideoReader(corrupted_video_path)
    with pytest.raises((VideoOpenError, InvalidVideoError)):
        reader.open()


def test_context_manager_opens_and_closes(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        assert reader.properties.frame_count == REAL_VIDEO_FRAME_COUNT


def test_properties_raises_before_open(real_video_path: Path) -> None:
    reader = VideoReader(real_video_path)
    with pytest.raises(InvalidVideoError):
        _ = reader.properties


def test_capture_raises_before_open(real_video_path: Path) -> None:
    reader = VideoReader(real_video_path)
    with pytest.raises(VideoOpenError):
        _ = reader.capture


def test_close_releases_the_capture(real_video_path: Path) -> None:
    reader = VideoReader(real_video_path)
    reader.open()
    reader.close()
    with pytest.raises(VideoOpenError):
        _ = reader.capture


def test_close_is_safe_to_call_twice(real_video_path: Path) -> None:
    reader = VideoReader(real_video_path)
    reader.open()
    reader.close()
    reader.close()
