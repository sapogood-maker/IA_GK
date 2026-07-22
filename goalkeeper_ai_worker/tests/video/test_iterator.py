"""Testes de FrameIterator - iteração segura, protocolo padrão do Python."""
from __future__ import annotations

from pathlib import Path

from worker.video.iterator import FrameIterator
from worker.video.provider import FrameProvider
from worker.video.reader import VideoReader


def test_iterates_over_all_frames_and_stops_cleanly(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        count = 0
        for frame in FrameIterator(provider):
            count += 1
            assert frame.image is not None

    assert count == 10


def test_iterator_implements_the_standard_protocol(real_video_path: Path) -> None:
    with VideoReader(real_video_path) as reader:
        provider = FrameProvider(reader)
        iterator = FrameIterator(provider)
        assert iter(iterator) is iterator
        frames = list(iterator)

    assert len(frames) == 10
    assert [f.metadata.frame_index for f in frames] == list(range(10))
