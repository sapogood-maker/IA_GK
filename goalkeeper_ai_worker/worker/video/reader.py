"""VideoReader: abre/fecha o arquivo de video, valida, expoe propriedades.

Usa OpenCV (cv2.VideoCapture) exclusivamente como biblioteca de LEITURA -
nenhum cv2.dnn, nenhum modelo, nenhuma inferencia, nenhuma GPU (Sprint W5,
AI_WORKER_CONSTITUTION.md Secao 15).
"""
from __future__ import annotations

from pathlib import Path

import cv2

from worker.video.exceptions import InvalidVideoError, VideoOpenError
from worker.video.types import VideoProperties


class VideoReader:
    """Abre um arquivo de video, valida seus metadados e expoe VideoProperties."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._capture: cv2.VideoCapture | None = None
        self._properties: VideoProperties | None = None

    def open(self) -> None:
        """Abre o arquivo e valida que e um video legivel com metadados coerentes."""
        if not self._path.exists():
            raise VideoOpenError(f"Arquivo de video nao encontrado: {self._path}")

        capture = cv2.VideoCapture(str(self._path))
        if not capture.isOpened():
            capture.release()
            raise VideoOpenError(f"Nao foi possivel abrir o video: {self._path}")

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if frame_count <= 0 or fps <= 0 or width <= 0 or height <= 0:
            capture.release()
            raise InvalidVideoError(
                f"Video invalido ou sem metadados legiveis: {self._path} "
                f"(frame_count={frame_count}, fps={fps}, width={width}, height={height})"
            )

        self._capture = capture
        self._properties = VideoProperties(
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
            duration_seconds=frame_count / fps,
        )

    def close(self) -> None:
        """Fecha o arquivo de video, liberando o recurso do OpenCV."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def properties(self) -> VideoProperties:
        """Propriedades do video - exige open() ter sido chamado antes."""
        if self._properties is None:
            raise InvalidVideoError("VideoReader.open() precisa ser chamado antes de acessar properties")
        return self._properties

    @property
    def capture(self) -> cv2.VideoCapture:
        """Handle bruto do OpenCV - uso interno de FrameProvider."""
        if self._capture is None:
            raise VideoOpenError("VideoReader.open() precisa ser chamado antes de ler frames")
        return self._capture

    def __enter__(self) -> VideoReader:
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
