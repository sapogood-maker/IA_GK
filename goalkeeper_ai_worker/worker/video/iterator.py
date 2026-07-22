"""FrameIterator: iteracao segura sobre os frames de um FrameProvider.

Implementa o protocolo padrao de iterador do Python (__iter__/__next__) -
para no fim normal do video via StopIteration; uma falha real de leitura
(FrameReadError) se propaga normalmente, nunca e mascarada como fim de
video.
"""
from __future__ import annotations

from worker.video.frame import Frame
from worker.video.provider import FrameProvider


class FrameIterator:
    """Itera sequencialmente sobre os frames de um FrameProvider."""

    def __init__(self, provider: FrameProvider) -> None:
        self._provider = provider

    def __iter__(self) -> FrameIterator:
        return self

    def __next__(self) -> Frame:
        frame = self._provider.read_next()
        if frame is None:
            raise StopIteration
        return frame
