"""Enricher: contrato de quem deriva novos Events a partir de uma
sequencia de eventos ja cronologica (Sprint W31).

Mesma disciplina de Detector/Tracker/SceneAnalyzer/WorldModel/Analyzer/
SegmentStrategy: quem orquestra (`EnrichmentPipeline`, pipeline.py) so
conhece este contrato, nunca o Enricher concreto - adicionar um Enricher
novo nunca exige alterar o Pipeline nem qualquer outro Enricher.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from worker.timeline.event import Event


class Enricher(ABC):
    """Uma unica responsabilidade: observar transicoes/padroes numa
    sequencia de eventos e devolver os NOVOS eventos derivados - nunca
    reemite os originais, nunca decide/julga."""

    name: str

    @abstractmethod
    def enrich(self, events: list[dict]) -> list[Event]:
        """`events`: a Timeline inteira (TimelineExplorer.chronological())
        ou os eventos de um unico PlaySegment - o Enricher nao sabe nem
        precisa saber qual dos dois modos e este (ver documento
        arquitetural W31, Secao 6). Todos os Enrichers desta sprint
        recebem exatamente a MESMA lista de entrada - nenhum consome a
        saida de outro Enricher."""
        ...
