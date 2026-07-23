"""AnalyzerContext: memória interna opcional entre chamadas sucessivas de
Analyzer.analyze() - análogo a WorldModelContext (W11)/
FootballDomainContext (W12), mas nesta sprint nenhum Analyzer precisa
dela: `GoalkeeperPresenceAnalyzer` é totalmente sem estado (cada
FootballWorld já é uma fotografia completa; `analyze()` não acumula nada
entre frames).

Reservada para Analyzers futuros que precisem lembrar de frames
anteriores (ex.: um `ShotAnalyzer` que precise da velocidade da bola nos
últimos N frames para detectar um chute) - eles podem compor esta classe
(ou uma subclasse própria) em seu próprio `__init__`, seguindo o mesmo
padrão de `WorldModelContext`/`FootballDomainContext`: instância privada
do Analyzer, limpa via `reset()` no início de cada Job (Seção 6.1,
"Estado entre Jobs")."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnalyzerContext:
    """Base vazia - Analyzers stateful futuros estendem com os campos que
    precisarem memorizar entre chamadas de `analyze()`."""

    def reset(self) -> None:
        """Default no-op - sobrescrever se campos forem adicionados."""
