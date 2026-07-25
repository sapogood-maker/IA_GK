"""EntityCorrelationEnricher: Nivel 2 (documento arquitetural W31, Secao
3) - NAO implementado nesta sprint, so a interface.

Correlacionaria ObjectDetected (tem posicao, sem track_id) com
TrackUpdated (tem track_id, sem posicao) ao longo de VARIOS frames -
diferente de TrackRecoveryConfidenceEnricher (track_recovery.py), que
correlaciona so DENTRO do mesmo frame. Rastrear atraves de multiplos
frames tem ambiguidade real quando ha mais de uma deteccao do mesmo
rotulo por frame - risco alto demais para entrar junto do nucleo seguro
(Nivel 1) desta sprint.

Cobriria, no futuro: ObjectApproaching, ObjectMovingAway,
DistanceThresholdCrossed, ObjectClosestToBallChanged, DirectionChanged.
"""
from __future__ import annotations

from worker.timeline.enrichment.enricher import Enricher
from worker.timeline.event import Event


class EntityCorrelationEnricher(Enricher):
    name = "entity_correlation"

    def enrich(self, events: list[dict]) -> list[Event]:
        raise NotImplementedError(
            "EntityCorrelationEnricher (Nivel 2) - interface definida no documento "
            "arquitetural da Sprint W31; implementacao de verdade fica para uma "
            "sprint futura, com uma estrategia explicita de desambiguacao."
        )
