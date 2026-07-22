"""Confirma que as excecoes de video derivam de WorkerError."""
from __future__ import annotations

from worker.core.exceptions import WorkerError
from worker.video.exceptions import FrameReadError, InvalidVideoError, VideoError, VideoOpenError


def test_all_video_exceptions_derive_from_worker_error() -> None:
    assert issubclass(VideoError, WorkerError)
    assert issubclass(VideoOpenError, VideoError)
    assert issubclass(InvalidVideoError, VideoError)
    assert issubclass(FrameReadError, VideoError)
