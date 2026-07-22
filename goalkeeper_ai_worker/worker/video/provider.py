"""FrameProvider: fornece acesso sequencial aos frames de um VideoReader
ja aberto.

Nao decide o que fazer com os frames - isso e responsabilidade de quem
consome (ex.: um InferenceEngine). So le e devolve.
"""
from __future__ import annotations

from worker.video.exceptions import FrameReadError
from worker.video.frame import Frame
from worker.video.metadata import FrameMetadata
from worker.video.reader import VideoReader


class FrameProvider:
    """Le frames sequencialmente de um VideoReader ja aberto."""

    def __init__(self, reader: VideoReader) -> None:
        self._reader = reader
        self._next_index = 0

    def read_next(self) -> Frame | None:
        """Le o proximo frame sequencial.

        Retorna None ao chegar ao fim esperado do video (indice atual ja
        alcancou frame_count - fim normal, nao e erro). Levanta
        FrameReadError se a leitura falhar antes disso - vídeo com menos
        frames legiveis do que o metadado declarado (corrupcao parcial)."""
        properties = self._reader.properties
        ok, image = self._reader.capture.read()
        if not ok:
            if self._next_index >= properties.frame_count:
                return None
            raise FrameReadError(
                f"Falha ao ler o frame {self._next_index} de {properties.frame_count} esperados"
            )
        metadata = FrameMetadata(
            frame_index=self._next_index,
            timestamp_seconds=self._next_index / properties.fps,
            position_seconds=self._next_index / properties.fps,
            fps=properties.fps,
            width=properties.width,
            height=properties.height,
            duration_seconds=properties.duration_seconds,
        )
        frame = Frame(image=image, metadata=metadata)
        self._next_index += 1
        return frame

    def frame_count(self) -> int:
        """Contagem total de frames esperada, conforme o metadado do video."""
        return self._reader.properties.frame_count
