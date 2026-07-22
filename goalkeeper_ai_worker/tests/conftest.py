"""Fixtures compartilhadas dos testes do Worker."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest

from worker.config.settings import get_settings


@pytest.fixture(autouse=True)
def _worker_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Garante variaveis de ambiente minimas e limpa o cache de settings entre testes."""
    monkeypatch.setenv("WORKER_INSTANCE_ID", "worker-test-01")
    monkeypatch.setenv("WORKER_ENV", "test")
    monkeypatch.setenv("WORKER_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("WORKER_BACKEND_API_URL", "http://backend.test")
    monkeypatch.setenv("WORKER_API_KEY", "test-api-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


REAL_VIDEO_FRAME_COUNT = 10
REAL_VIDEO_FPS = 10.0
REAL_VIDEO_WIDTH = 64
REAL_VIDEO_HEIGHT = 48


@pytest.fixture
def real_video_path(tmp_path: Path) -> Path:
    """Gera um vídeo real e mínimo (10 frames, 64x48, 10fps) com OpenCV -
    nunca mockado. Usado por tests/video/ e tests/inference/."""
    path = tmp_path / "real_video.avi"
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(str(path), fourcc, REAL_VIDEO_FPS, (REAL_VIDEO_WIDTH, REAL_VIDEO_HEIGHT))
    for i in range(REAL_VIDEO_FRAME_COUNT):
        frame = np.full((REAL_VIDEO_HEIGHT, REAL_VIDEO_WIDTH, 3), i * 20 % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def corrupted_video_path(tmp_path: Path) -> Path:
    """Um arquivo com extensão de vídeo, mas conteúdo inválido."""
    path = tmp_path / "corrupted.avi"
    path.write_bytes(b"isto nao e um video de verdade")
    return path


@pytest.fixture
def missing_video_path(tmp_path: Path) -> Path:
    """Um caminho que não existe."""
    return tmp_path / "does_not_exist.avi"
