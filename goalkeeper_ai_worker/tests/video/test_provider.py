"""Testes de FrameProvider - leitura sequencial real de frames."""
from __future__ import annotations

from pathlib import Path

from worker.video.provider import FrameProvider
from worker.video.reader import VideoReader


def test_read_next_returns_frames_in_order(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        frames = []
        while True:
            frame = provider.read_next()
            if frame is None:
                break
            frames.append(frame)

    assert len(frames) == 10
    assert [f.metadata.frame_index for f in frames] == list(range(10))


def test_frame_count_matches_video_properties(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        assert provider.frame_count() == 10


def test_frame_metadata_has_correct_video_level_properties(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        frame = provider.read_next()
        props = reader.properties

    assert frame is not None
    assert frame.metadata.frame_index == 0
    assert frame.metadata.timestamp_seconds == 0.0
    assert frame.metadata.fps == props.fps
    assert frame.metadata.width == props.width
    assert frame.metadata.height == props.height
    assert frame.metadata.duration_seconds == props.duration_seconds


def test_read_next_returns_none_after_last_frame(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        for _ in range(10):
            assert provider.read_next() is not None
        assert provider.read_next() is None
