"""Constantes de tipo de evento DERIVADO (Sprint W31) - modulo proprio,
paralelo a worker/timeline/event_types.py (nao o altera, nao compartilha
namespace de constantes). Nenhum valor aqui pode colidir com um valor ja
existente la (garantido por teste - tests/timeline/enrichment/
test_event_types_do_not_collide.py).

So os tipos de Nivel 1 do documento arquitetural da W31 (seguros, sem
correlacao ambigua entre frames). Nivel 2 (ObjectApproaching,
ObjectMovingAway, DistanceThresholdCrossed, ObjectClosestToBallChanged,
DirectionChanged) fica fora desta sprint - ver
worker/timeline/enrichment/enrichers/entity_correlation.py.
"""
from __future__ import annotations

MOTION_STARTED = "MotionStarted"
MOTION_STOPPED = "MotionStopped"
OBJECT_STATIONARY = "ObjectStationary"

TRACK_STABLE = "TrackStable"
TRACK_UNSTABLE = "TrackUnstable"
TRACK_RECOVERED_WITH_CONFIDENCE = "TrackRecoveredWithConfidence"

BALL_MOTION_STARTED = "BallMotionStarted"
BALL_MOTION_STOPPED = "BallMotionStopped"
GOALKEEPER_MOVEMENT_STARTED = "GoalkeeperMovementStarted"
GOALKEEPER_MOVEMENT_STOPPED = "GoalkeeperMovementStopped"

# MotionTransitionEnricher e uma UNICA implementacao parametrizada por
# entity_filter (rotulo normalizado) - nao uma classe por rotulo. Este
# mapeamento decide qual par (started, stopped) usar; None (generico) e
# o padrao quando entity_filter nao bate com nenhuma entrada aqui.
MOTION_EVENT_TYPES_BY_ENTITY: dict[str, tuple[str, str]] = {
    "ball": (BALL_MOTION_STARTED, BALL_MOTION_STOPPED),
    "goalkeeper": (GOALKEEPER_MOVEMENT_STARTED, GOALKEEPER_MOVEMENT_STOPPED),
}
DEFAULT_MOTION_EVENT_TYPES: tuple[str, str] = (MOTION_STARTED, MOTION_STOPPED)
