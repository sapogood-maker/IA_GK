"""SegmentStrategy: contrato de quem decide ONDE cortar a Timeline em
segmentos (Sprint W30).

Mesma disciplina de Detector/Tracker/SceneAnalyzer/WorldModel/Analyzer:
`PlaySegmenter` (segmenter.py) so conhece este contrato, nunca a
estrategia concreta - trocar/adicionar uma estrategia (continuidade de
track, continuidade da bola, composta) nunca exige alterar
PlaySegmenter/PlaySegment."""
from __future__ import annotations

from abc import ABC, abstractmethod


class SegmentStrategy(ABC):
    """Uma unica responsabilidade: decidir os intervalos [start_frame,
    end_frame] de cada segmento, a partir de uma sequencia de eventos ja
    cronologica."""

    name: str

    @abstractmethod
    def find_boundaries(self, events: list[dict]) -> list[tuple[int, int]]:
        """`events` ja em ordem cronologica (TimelineExplorer.chronological()).
        Devolve uma lista de (start_frame, end_frame), um par por segmento,
        em ordem. Nao constroi PlaySegment - so decide os limites."""
        ...
